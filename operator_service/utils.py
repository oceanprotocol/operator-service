import json
import os
import uuid
import logging

from kubernetes.client.rest import ApiException
from ocean_keeper import Keeper

from operator_service.exceptions import InvalidSignatureError

logger = logging.getLogger(__name__)


def generate_new_id():
    """
    Generate a new id without prefix.
    :return: Id, str
    """
    return uuid.uuid4().hex


def create_compute_job(workflow, execution_id, group, version, namespace):
    execution = dict()
    execution['apiVersion'] = group + '/' + version
    execution['kind'] = 'WorkFlow'
    execution['metadata'] = dict()
    execution['metadata']['name'] = execution_id
    execution['metadata']['namespace'] = namespace
    execution['metadata']['labels'] = dict()
    execution['metadata']['labels']['workflow'] = execution_id
    execution['spec'] = dict()
    execution['spec']['metadata'] = workflow
    return execution


def check_required_attributes(required_attributes, data, method):
    logger.info('got %s request: %s' % (method, data))
    if not data or not isinstance(data, dict):
        logger.error('%s request failed: data is empty.' % method)
        return 'payload seems empty.', 400

    for attr in required_attributes:
        if attr not in data:
            logger.error('%s request failed: required attr %s missing.' % (method, attr))
            return '"%s" is required in the call to %s' % (attr, method), 400

    return None, None


def process_signature_validation(signature, original_msg):
    if is_verify_signature_required():
        # verify provider's signature
        allowed_providers = get_list_of_allowed_providers()
        if not signature:
            return f'`providerSignature` of agreementId is required.', 400

        try:
            verify_signature(signature, original_msg, allowed_providers)
        except InvalidSignatureError as e:
            return f'{e}', 401

    return '', None


def verify_signature(signature, original_msg, allowed_addresses):
    address = Keeper.personal_ec_recover(original_msg, signature)
    if address.lower() in allowed_addresses:
        return

    msg = f'Invalid signature {signature} of documentId {original_msg},' \
          f'the signing ethereum account {address} is not authorized to use this service.'
    raise InvalidSignatureError(msg)


def get_list_of_allowed_providers():
    try:
        config_allowed_list = json.loads(os.getenv("ALLOWED_PROVIDERS"))
        if not isinstance(config_allowed_list, list):
            logger.error('Failed loading ALLOWED_PROVIDERS')
            return []
        return config_allowed_list
    except ApiException as e:
        logging.error(f'Exception when calling json.loads(os.getenv("ALLOWED_PROVIDERS")): {e}')
        return []


def is_verify_signature_required():
    try:
        return bool(int(os.environ.get('SIGNATURE_REQUIRED', 0)) == 1)
    except ValueError:
        return False


def get_compute_resources():
    resources = dict()
    resources['inputVolumesize'] = os.environ.get('inputVolumesize', "1Gi")
    resources['outputVolumesize'] = os.environ.get('outputVolumesize', "1Gi")
    resources['adminlogsVolumesize'] = os.environ.get('adminlogsVolumesize', "1Gi")
    resources['requests_cpu'] = os.environ.get('requests_cpu', "200m")
    resources['requests_memory'] = os.environ.get('requests_memory', "100Mi")
    resources['limits_cpu'] = os.environ.get('limits_cpu', "1")
    resources['limits_memory'] = os.environ.get('limits_memory', "500Mi")
    return resources

def get_namespace_configs():
    resources = dict()
    resources['namespace'] = os.environ.get('DEFAULT_NAMESPACE', "ocean-compute")
    return resources
