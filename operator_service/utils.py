from decimal import Decimal
import json
import os
import uuid
import logging
import mimetypes
from cgi import parse_header
from os import getenv

from kubernetes.client.rest import ApiException
from eth_keys import KeyAPI
from eth_keys.backends import NativeECCBackend
from flask import Response, request
from operator_service.exceptions import InvalidSignatureError
from web3 import Web3

logger = logging.getLogger(__name__)
keys = KeyAPI(NativeECCBackend)


def generate_new_id():
    """
    Generate a new id without prefix.
    :return: Id, str
    """
    return uuid.uuid4().hex


def create_compute_job(workflow, execution_id, group, version, namespace):
    execution = dict()
    execution["apiVersion"] = group + "/" + version
    execution["kind"] = "WorkFlow"
    execution["metadata"] = dict()
    execution["metadata"]["name"] = execution_id
    execution["metadata"]["namespace"] = namespace
    execution["metadata"]["labels"] = dict()
    execution["metadata"]["labels"]["workflow"] = execution_id
    execution["spec"] = dict()
    execution["spec"]["metadata"] = workflow
    return execution


def check_required_attributes(required_attributes, data, method):
    logger.debug("got %s request: %s" % (method, data))
    if not data or not isinstance(data, dict):
        logger.error("%s request failed: data is empty." % method)
        return "payload seems empty.", 400

    for attr in required_attributes:
        if attr not in data:
            logger.error(
                "%s request failed: required attr %s missing." % (method, attr)
            )
            return '"%s" is required in the call to %s' % (attr, method), 400

    return None, None


def get_signer(signature, message):
    """
    Returns signer of a message.
    """

    signature_bytes = Web3.toBytes(hexstr=signature)
    if signature_bytes[64] == 27:
        new_signature = b"".join([signature_bytes[0:64], b"\x00"])
    elif signature_bytes[64] == 28:
        new_signature = b"".join([signature_bytes[0:64], b"\x01"])
    else:
        new_signature = signature_bytes
    signature = keys.Signature(signature_bytes=new_signature)
    message_hash = Web3.solidityKeccak(
        ["bytes"],
        [Web3.toBytes(text=message)],
    )
    prefix = "\x19Ethereum Signed Message:\n32"
    signable_hash = Web3.solidityKeccak(
        ["bytes", "bytes"], [Web3.toBytes(text=prefix), Web3.toBytes(message_hash)]
    )
    vkey = keys.ecdsa_recover(signable_hash, signature)
    return vkey.to_address()


def process_provider_signature_validation(signature, original_msg, nonce):
    if not signature or not original_msg:
        return f"`providerSignature` of agreementId is required.", 400, None
    original_msg = f"{original_msg}{nonce}"
    try:
        address = get_signer(signature, original_msg)
    except Exception as e:
        return "Failed to recover address", 400, None
    if is_verify_signature_required():
        # verify provider's signature
        allowed_providers = get_list_of_allowed_providers()
        if address.lower() not in allowed_providers:
            msg = (
                f"Invalid signature {signature} of documentId {original_msg},"
                f"the signing ethereum account {address} is not authorized to use this service."
            )
            return msg, 401, None

    return "", None, address


def get_list_of_allowed_providers():
    try:
        config_allowed_list = json.loads(os.getenv("ALLOWED_PROVIDERS"))
        if not isinstance(config_allowed_list, list):
            logger.error("Failed loading ALLOWED_PROVIDERS")
            return []
        return config_allowed_list
    except ApiException as e:
        logging.error(
            f'Exception when calling json.loads(os.getenv("ALLOWED_PROVIDERS")): {e}'
        )
        return []


def is_verify_signature_required():
    try:
        return bool(int(os.environ.get("SIGNATURE_REQUIRED", 0)) == 1)
    except ValueError:
        return False


def get_compute_resources():
    resources = dict()
    resources["inputVolumesize"] = os.environ.get("inputVolumesize", "1Gi")
    resources["outputVolumesize"] = os.environ.get("outputVolumesize", "1Gi")
    resources["adminlogsVolumesize"] = os.environ.get("adminlogsVolumesize", "1Gi")
    resources["requests_cpu"] = os.environ.get("requests_cpu", "200m")
    resources["requests_memory"] = os.environ.get("requests_memory", "100Mi")
    resources["limits_cpu"] = os.environ.get("limits_cpu", "1")
    resources["limits_memory"] = os.environ.get("limits_memory", "500Mi")
    return resources


def get_namespace_configs():
    resources = dict()
    resources["namespace"] = os.environ.get("DEFAULT_NAMESPACE", "ocean-compute")
    return resources


def build_download_response(request, requests_session, url, content_type=None):
    try:
        download_request_headers = {}
        download_response_headers = {}
        is_range_request = bool(request.range)

        if is_range_request:
            download_request_headers = {"Range": request.headers.get("range")}
            download_response_headers = download_request_headers
        # IPFS utils
        ipfs_x_api_key = getenv("X-API-KEY", None)
        if ipfs_x_api_key:
            download_request_headers["X-API-KEY"] = ipfs_x_api_key
        ipfs_client_id = getenv("CLIENT-ID", None)
        if ipfs_client_id:
            download_request_headers["CLIENT-ID"] = ipfs_client_id

        response = requests_session.get(
            url, headers=download_request_headers, stream=True, timeout=3
        )

        if not is_range_request:
            filename = url.split("/")[-1]

            content_disposition_header = response.headers.get("content-disposition")
            if content_disposition_header:
                _, content_disposition_params = parse_header(content_disposition_header)
                content_filename = content_disposition_params.get("filename")
                if content_filename:
                    filename = content_filename

            content_type_header = response.headers.get("content-type")
            if content_type_header:
                content_type = content_type_header

            file_ext = os.path.splitext(filename)[1]
            if file_ext and not content_type:
                content_type = mimetypes.guess_type(filename)[0]
            elif not file_ext and content_type:
                # add an extension to filename based on the content_type
                extension = mimetypes.guess_extension(content_type)
                if extension:
                    filename = filename + extension

            download_response_headers = {
                "Content-Disposition": f"attachment;filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition",
            }

        def _generate(_response):
            for chunk in _response.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk

        return Response(
            _generate(response),
            response.status_code,
            headers=download_response_headers,
            content_type=content_type,
        )
    except Exception as e:
        logger.error(f"Error preparing file download response: {str(e)}")
        raise


def sanitize_response_for_provider(d):
    """
    Sanitize objects to send them to provider by recursively convert Decimal and float values to string
    in: dict | list | tuple | set | str | int | float | None
    out: dict | list | tuple | set | str | int | float | None
    """
    if isinstance(d, Decimal):
        return str(d)
    elif isinstance(d, float):
        return str(d)
    elif isinstance(d, dict):
        return {
            sanitize_response_for_provider(k): sanitize_response_for_provider(v)
            for k, v in d.items()
        }
    elif isinstance(d, list):
        return [sanitize_response_for_provider(element) for element in d]
    else:
        return d
