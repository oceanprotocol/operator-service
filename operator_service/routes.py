import os
from os import path
import logging
import json

import kubernetes
from flask import Blueprint, request, Response
from kubernetes.client.rest import ApiException

from operator_service.config import Config
from operator_service.data_store import (
    create_sql_job,
    get_sql_status,
    get_sql_jobs,
    stop_sql_job,
    remove_sql_job,
    get_sql_running_jobs,
    get_sql_job_urls,
    get_sql_environments,
    check_environment_exists,
)
from operator_service.kubernetes_api import KubeAPI
from operator_service.utils import (
    create_compute_job,
    check_required_attributes,
    sanitize_response_for_provider,
    generate_new_id,
    process_provider_signature_validation,
    get_compute_resources,
    get_namespace_configs,
    build_download_response,
)
from requests.adapters import HTTPAdapter
from requests.sessions import Session

logger = logging.getLogger(__name__)

services = Blueprint("services", __name__)

standard_headers = {"Content-type": "application/json", "Connection": "close"}

# Configuration to connect to k8s.
if not path.exists("/.dockerenv"):
    kubernetes.config.load_kube_config()
else:
    kubernetes.config.load_incluster_config()

config = Config()


@services.route("/compute", methods=["POST"])
def start_compute_job():
    """
    Create and start the compute job
    ---
    tags:
      - operation
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: false
        description: Init workflow.
        schema:
          workflow:
          nullable: true
          example: {
                        "agreementId":"0x111111",
                        "owner":"0xC41808BBef371AD5CFc76466dDF9dEe228d2BdAA",
                        "providerSignature":"0xc3e6de65bfa3527409d8df6232e084e3cea0bae3bc85f7401e98fac56f9706157e42089b4b2b45f0f019bc94e7e4806afe8c86a6bab9c616d5010891e0246e761c",
                        "environment":"ocean-compute",
                        "nonce": 1234,
                        "workflow":{
                            "stages": [
                              {
                                "index": 0,
                                "input": [
                                    {
                                        "id": "did:op:87bdaabb33354d2eb014af5091c604fb4b0f67dc6cca4d18a96547bffdc27bcf",
                                        "url": [
                                            "https://data.ok.gov/sites/default/files/unspsc%20codes_3.csv"
                                        ],
                                        "index": 0
                                    },
                                    {
                                        "id": "did:op:0c47cf2a09ae137eb473b6f9bb3dbb81ff4df8a69770253c0ff1f9e3c5f4639d",
                                        "url": [
                                            "https://data.ct.gov/api/views/2fi9-sgi3/rows.csv?accessType=DOWNLOAD"
                                        ],
                                        "index": 1
                                    }
                                ],
                                "compute": {},
                                "algorithm": {
                                    "id": "did:op:87bdaabb33354d2eb014af5091c604fb4b0f67dc6cca4d18a96547bffdc27bcf",
                                    "url": "https://raw.githubusercontent.com/oceanprotocol/test-algorithm/master/javascript/algo.js",
                                    "rawcode": "console.log('this is a test')",
                                    "container": {
                                        "image": "node",
                                        "tag": "10",
                                        "entrypoint": "node $ALGO"
                                    }
                                },
                                "output": {
                                    "nodeUri": "https://nile.dev-ocean.com",
                                    "brizoUri": "https://brizo.marketplace.dev-ocean.com",
                                    "brizoAddress": "0x4aaab179035dc57b35e2ce066919048686f82972",
                                    "metadata": {
                                        "name": "Workflow output"
                                    },
                                    "metadataUri": "https://aquariusv4.oceanprotocol.com/",
                                    "secretStoreUri": "https://secret-store.nile.dev-ocean.com",
                                    "whitelist": [
                                        "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e",
                                        "0xACBd138aBD70e2F00903268F3Db08f2D25677C9e"
                                    ],
                                    "owner":"0xC41808BBef371AD5CFc76466dDF9dEe228d2BdAA",
                                    "publishOutput":true,
                                    "publishAlgorithmLog":true
                                  }
                              }
                            ]
                          }
                        }
    response:
      201:
        description: Workflow inited successfully.
      400:
        description: Some error
    """

    data = request.args if request.args else request.json
    required_attributes = [
        "workflow",
        "agreementId",
        "owner",
        "providerSignature",
        "environment",
        "nonce",
    ]
    msg, status = check_required_attributes(required_attributes, data, "POST:/compute")
    if msg:
        return Response(json.dumps({"error": msg}), status, headers=standard_headers)

    workflow = data.get("workflow")
    agreement_id = data.get("agreementId")
    owner = data.get("owner")
    nonce = data.get("nonce")
    if not workflow:
        return Response(
            json.dumps(
                {
                    "error": f"`workflow` is required in the payload and must "
                    f"include workflow stages"
                }
            ),
            400,
            headers=standard_headers,
        )
    environment = data.get("environment")
    if not check_environment_exists(environment):
        logger.error(f"Environment invalid or does not exists")
        return Response(
            json.dumps({"error": "Environment invalid or does not exists"}),
            400,
            headers=standard_headers,
        )
    # verify provider's signature
    msg, status, provider_address = process_provider_signature_validation(
        data.get("providerSignature"), f"{owner}", nonce
    )
    if msg:
        return Response(json.dumps({"error": msg}), status, headers=standard_headers)

    stages = workflow.get("stages")
    if not stages:
        logger.error(f"Missing stages")
        return Response(
            json.dumps({"error": "Missing stages"}), 400, headers=standard_headers
        )
    if len(stages) > 1:
        logger.error(f"Multiple stages are not supported yet")
        return Response(
            json.dumps({"error": "Multiple stages are not supported yet"}),
            400,
            headers=standard_headers,
        )
    for _attr in ("algorithm", "compute", "input", "output"):
        if _attr not in stages[0]:
            logger.error(f"Missing {_attr} in stage 0")
            return Response(
                json.dumps({"error": f"Missing {_attr} in stage 0"}),
                400,
                headers=standard_headers,
            )
    job_id = generate_new_id()
    logger.info(f"Got job_id: {job_id}")
    body = create_compute_job(
        workflow, job_id, config.group, config.version, environment
    )
    body["metadata"]["secret"] = generate_new_id()
    logger.debug(f"Got body: {body}")
    create_sql_job(
        agreement_id, str(job_id), owner, body, environment, provider_address
    )
    status_list = get_sql_status(agreement_id, str(job_id), owner)

    return Response(
        json.dumps(sanitize_response_for_provider(status_list)),
        200,
        headers=standard_headers,
    )


@services.route("/compute", methods=["PUT"])
def stop_compute_job():
    """
    Stop the current compute job..
    ---
    tags:
      - operation
    consumes:
      - application/json
    parameters:
      - name: agreementId
        in: query
        description: agreementId
        type: string
      - name: jobId
        in: query
        description: Id of the job.
        type: string
      - name: owner
        in: query
        description: owner
        type: string
      - name: providerSignature
        in: query
        description: providerSignature
        type: string
      - name: nonce
        in: query
        description: nonce
    """
    try:
        data = request.args if request.args else request.json
        required_attributes = ["owner", "providerSignature", "nonce"]
        msg, status = check_required_attributes(
            required_attributes, data, "PUT:/compute"
        )
        if msg:
            return Response(
                json.dumps({"error": msg}), status, headers=standard_headers
            )
        if data is None:
            msg = f"You have to specify one of agreementId, jobId or owner"
            return Response(json.dumps({"error": msg}), 400, headers=standard_headers)

        agreement_id = data.get("agreementId", None)
        owner = data.get("owner", None)
        job_id = data.get("jobId", None)
        if not agreement_id or len(agreement_id) < 2:
            agreement_id = None

        if not job_id or len(job_id) < 2:
            job_id = None

        if not owner or len(owner) < 2:
            owner = None
        if owner is None and agreement_id is None and job_id is None:
            msg = f"You have to specify one of agreementId, jobId or owner"
            logger.error(msg)
            return Response(json.dumps({"error": msg}), 400, headers=standard_headers)
        nonce = data.get("nonce")
        # verify provider's signature
        if job_id:
            sign_message = f"{owner}{job_id}"
        else:
            sign_message = f"{owner}"
        msg, status, provider_address = process_provider_signature_validation(
            data.get("providerSignature"), sign_message, nonce
        )
        if msg:
            return Response(
                json.dumps({"error": msg}), status, headers=standard_headers
            )
        jobs_list = get_sql_jobs(agreement_id, job_id, owner)
        for ajob in jobs_list:
            name = ajob
            logger.info(f"Stopping job : {name}")
            stop_sql_job(name)

        status_list = get_sql_status(agreement_id, job_id, owner)
        return Response(json.dumps(status_list), 200, headers=standard_headers)

    except ApiException as e:
        logger.error(f"Exception when stopping compute job: {e}")
        return Response(
            json.dumps({"error": f"Error stopping job: {e}"}),
            400,
            headers=standard_headers,
        )
    except Exception as e:
        msg = f"{e}"
        logger.error(msg)
        return Response(json.dumps({"error": msg}), 400, headers=standard_headers)


@services.route("/compute", methods=["DELETE"])
def delete_compute_job():
    """
    Deletes the current compute job.
    ---
    tags:
      - operation
    consumes:
      - application/json
    parameters:
      - name: agreementId
        in: query
        description: agreementId
        type: string
      - name: jobId
        in: query
        description: Id of the job.
        type: string
      - name: owner
        in: query
        description: owner
        type: string
      - name: providerSignature
        in: query
        description: providerSignature
        type: string
    """
    # since op-engine handles this, there is no need for this endpoint. Will just keep it here for backwards compat
    return Response(json.dumps(""), 200, headers=standard_headers)


@services.route("/compute", methods=["GET"])
def get_compute_job_status():
    """
    Get status for an specific or multiple jobs.
    ---
    tags:
      - operation
    consumes:
      - application/json
    parameters:
      - name: agreementId
        in: query
        description: agreementId
        type: string
      - name: jobId
        in: query
        description: Id of the job.
        type: string
      - name: owner
        in: query
        description: owner
        type: string
      - name: providerSignature
        in: query
        description: providerSignature
        type: string
      - name: nonce
        in: query
        description: nonce
    responses:
      200:
        description: Get correctly the status
      400:
        description: Error
    """
    try:
        data = request.args if request.args else request.json
        if data is None:
            msg = f"You have to specify one of agreementId, jobId or owner"
            return Response(json.dumps({"error": msg}), 400, headers=standard_headers)
        agreement_id = data.get("agreementId", None)
        owner = data.get("owner", None)
        job_id = data.get("jobId", None)

        if not agreement_id or len(agreement_id) < 2:
            agreement_id = None

        if not job_id or len(job_id) < 2:
            job_id = None

        if not owner or len(owner) < 2:
            owner = None

        if owner is None and agreement_id is None and job_id is None:
            msg = f"You have to specify one of agreementId, jobId or owner"
            logger.error(msg)
            return Response(json.dumps({"error": msg}), 400, headers=standard_headers)

        nonce = data.get("nonce", None)
        # verify provider's signature
        if job_id:
            sign_message = f"{owner}{job_id}"
        else:
            sign_message = f"{owner}"
        msg, status, provider_address = process_provider_signature_validation(
            data.get("providerSignature"), sign_message, nonce
        )
        if msg:
            return Response(
                json.dumps({"error": msg}), status, headers=standard_headers
            )
        logger.info(f"Got status request for {agreement_id}, {job_id}, {owner}")
        api_response = get_sql_status(agreement_id, job_id, owner)

        return Response(
            json.dumps(sanitize_response_for_provider(api_response)),
            200,
            headers=standard_headers,
        )

    except ApiException as e:
        msg = f"Error getting the status: {e}"
        logger.error(msg)
        return Response(json.dumps({"error": msg}), 400)
    except Exception as e:
        msg = f"{e}"
        logger.error(msg)
        return Response(json.dumps({"error": msg}), 400, headers=standard_headers)


@services.route("/runningjobs", methods=["GET"])
def get_running_jobs():
    """
    Get running jobs
    ---
    tags:
      - operation
    consumes:
      - application/json
    responses:
      200:
        description: Get correctly the status
    """
    try:
        api_response = get_sql_running_jobs()
        return Response(json.dumps(api_response), 200, headers=standard_headers)
    except ApiException as e:
        msg = f"Error getting the status: {e}"
        logger.error(msg)
        return Response(json.dumps({"error": msg}), 400, headers=standard_headers)
    except Exception as e:
        msg = f"{e}"
        logger.error(msg)
        return Response(json.dumps({"error": msg}), 400, headers=standard_headers)


@services.route("/getResult", methods=["GET"])
def get_indexed_result():
    """
    Get one result from a compute job, based on the index.
    ---
    tags:
      - operation
    consumes:
      - application/json
    parameters:
      - name: index
        in: query
        description: result index
        type: number
      - name: jobId
        in: query
        description: Id of the job.
        type: string
      - name: providerSignature
        in: query
        description: providerSignature
        type: string
      - name: owner
        in: query
        description: owner of the job
        type: string
    responses:
      200:
        description: File content
      400:
        description: Error
      404:
        description: Not found
    """
    try:
        requests_session = get_requests_session()
        data = request.args if request.args else request.json
        if data is None:
            msg = f"Both index & job_id are required"
            return Response(json.dumps({"error": msg}), 400, headers=standard_headers)
        required_attributes = ["owner", "providerSignature", "nonce", "index", "jobId"]
        msg, status = check_required_attributes(
            required_attributes, data, "GET:/getResult"
        )
        if msg:
            return Response(
                json.dumps({"error": msg}), status, headers=standard_headers
            )
        index = data.get("index", None)
        job_id = data.get("jobId", None)
        owner = data.get("owner", None)
        nonce = data.get("nonce", None)
        # verify provider's signature
        msg, status, provider_address = process_provider_signature_validation(
            data.get("providerSignature"), f"{owner}{job_id}", nonce
        )
        if msg:
            return Response(
                json.dumps({"error": msg}), status, headers=standard_headers
            )
        index = int(index)
        outputs, owner = get_sql_job_urls(job_id)
        # TO DO - check owner here & provider
        logger.info(f"Got {owner}")
        logger.info(f"Got {outputs}")
        if outputs is None or not isinstance(outputs, list):
            msg = f"No results for job {job_id}"
            return Response(json.dumps({"error": msg}), 404, headers=standard_headers)
        # check the index
        logger.info(f"Len outputs {len(outputs)}, index: {index}")
        if int(index) >= len(outputs):
            msg = f"No such index {index} in this compute job"
            return Response(json.dumps({"error": msg}), 404, headers=standard_headers)
        logger.info(f"Trying: {outputs[index]['url']}")
        return build_download_response(
            request, requests_session, outputs[index]["url"], None
        )

    except ApiException as e:
        msg = f"Error getting the status: {e}"
        logger.error(msg)
        return Response(json.dumps({"error": msg}), 400, headers=standard_headers)
    except Exception as e:
        msg = f"{e}"
        logger.error(msg)
        return Response(json.dumps({"error": msg}), 400, headers=standard_headers)


@services.route("/environments", methods=["GET"])
def get_environments():
    """
    Get environments
    ---
    tags:
      - operation
    consumes:
      - application/json
    responses:
      200:
        description: Get correctly the status
    """
    try:
        api_response = get_sql_environments(logger)
        return Response(json.dumps(api_response), 200, headers=standard_headers)
    except Exception as e:
        msg = f"{e}"
        logger.error(msg)
        return Response(json.dumps({"error": msg}), 400, headers=standard_headers)


def get_requests_session() -> Session:
    """
    Set connection pool maxsize and block value to avoid `connection pool full` warnings.
    :return: requests session
    """
    session = Session()
    session.mount(
        "http://", HTTPAdapter(pool_connections=25, pool_maxsize=25, pool_block=True)
    )
    session.mount(
        "https://", HTTPAdapter(pool_connections=25, pool_maxsize=25, pool_block=True)
    )
    return session
