import os
from os import path
import logging

import kubernetes
from flask import Blueprint, jsonify, request
from kubernetes.client.rest import ApiException

from operator_service.config import Config
from operator_service.data_store import create_sql_job, get_sql_status, get_sql_jobs, stop_sql_job, remove_sql_job, get_sql_running_jobs
from operator_service.kubernetes_api import KubeAPI
from operator_service.utils import (
    create_compute_job,
    check_required_attributes,
    generate_new_id,
    process_signature_validation,
    get_compute_resources,
    get_namespace_configs
)
logger = logging.getLogger('ocean-operator')
logger.setLevel(logging.DEBUG)

services = Blueprint('services', __name__)

# Configuration to connect to k8s.
if not path.exists('/.dockerenv'):
    kubernetes.config.load_kube_config()
else:
    kubernetes.config.load_incluster_config()

config = Config()


@services.route('/compute', methods=['POST'])
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
                        "providerSignature":"ae01",
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
                                        "id": "did:op:1384941e6f0b46299b6e515723df3d8e8e5d1fb175554467a1cb7bc613f5c72e",
                                        "url": [
                                            "https://data.ct.gov/api/views/2fi9-sgi3/rows.csv?accessType=DOWNLOAD"
                                        ],
                                        "index": 1
                                    }
                                ],
                                "compute": {
                                    "Instances": 1,
                                    "namespace": "withgpu",
                                    "maxtime": 3600
                                },
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
                                    "metadataUri": "https://aquarius.marketplace.dev-ocean.com",
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
        'workflow',
        'agreementId',
        'owner',
        'providerSignature'
    ]
    msg, status = check_required_attributes(required_attributes, data, 'POST:/compute')
    if msg:
        return jsonify(error=msg), status

    workflow = data.get('workflow')
    agreement_id = data.get('agreementId')
    owner = data.get('owner')
    if not workflow:
        return jsonify(error=f'`workflow` is required in the payload and must '
                       f'include workflow stages'), 400

    # verify provider's signature
    msg, status = process_signature_validation(data.get('providerSignature'), agreement_id)
    if msg:
        return jsonify(error=f'`providerSignature` of agreementId is required.'), status

    stages = workflow.get('stages')
    if not stages:
        logger.error(f'Missing stages')
        return jsonify(error='Missing stages'), 400

    for _attr in ('algorithm', 'compute', 'input', 'output'):
        if _attr not in stages[0]:
            logger.error(f'Missing {_attr} in stage 0')
            return jsonify(error=f'Missing {_attr} in stage 0'), 400
    # loop through stages and add resources
    timeout = int(os.getenv("ALGO_POD_TIMEOUT", 0))
    compute_resources_def = get_compute_resources()
    namespaces_def = get_namespace_configs()
    for count, astage in enumerate(workflow['stages']):
        # check timeouts
        if timeout > 0:
            if 'maxtime' in astage['compute']:
                maxtime = int(astage['compute']['maxtime'])
            else:
                maxtime = 0
            if timeout < maxtime or maxtime <= 0:
                astage['compute']['maxtime'] = timeout
                logger.debug(f"Maxtime in workflow was {maxtime}. Overwritten to {timeout}")
        # get resources
        astage['compute']['resources'] = compute_resources_def
        astage['compute']['namespace'] = namespaces_def['namespace']

    job_id = generate_new_id()
    logger.debug(f'Got job_id: {job_id}')
    body = create_compute_job(
        workflow, job_id, config.group, config.version, namespaces_def['namespace']
    )
    body['metadata']['secret'] = generate_new_id()
    logger.debug(f'Got body: {body}')
    create_sql_job(agreement_id, str(job_id), owner,body,namespaces_def['namespace'])
    status_list = get_sql_status(agreement_id, str(job_id), owner)
    return jsonify(status_list), 200


@services.route('/compute', methods=['PUT'])
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
    """
    try:
        data = request.args if request.args else request.json

        agreement_id = data.get('agreementId')
        owner = data.get('owner')
        job_id = data.get('jobId')

        if not agreement_id or len(agreement_id) < 2:
            agreement_id = None

        if not job_id or len(job_id) < 2:
            job_id = None

        if not owner or len(owner) < 2:
            owner = None
        if owner is None and agreement_id is None and job_id is None:
            msg = f'You have to specify one of agreementId, jobId or owner'
            logger.error(msg)
            return jsonify(error=msg), 400
        jobs_list = get_sql_jobs(agreement_id, job_id, owner)
        for ajob in jobs_list:
            name = ajob
            logger.info(f'Stopping job : {name}')
            stop_sql_job(name)

        status_list = get_sql_status(agreement_id, job_id, owner)
        return jsonify(status_list), 200

    except ApiException as e:
        logger.error(f'Exception when stopping compute job: {e}')
        return jsonify(error=f'Error stopping job: {e}'), 400


@services.route('/compute', methods=['DELETE'])
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
    """
    #since op-engine handles this, there is no need for this endpoint. Will just keep it here for backwards compat
    return jsonify(""), 200


@services.route('/compute', methods=['GET'])
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
    responses:
      200:
        description: Get correctly the status
      400:
        description: Error
    """
    try:
        data = request.args if request.args else request.json
        agreement_id = data.get('agreementId')
        owner = data.get('owner')
        job_id = data.get('jobId')

        if not agreement_id or len(agreement_id) < 2:
            agreement_id = None

        if not job_id or len(job_id) < 2:
            job_id = None

        if not owner or len(owner) < 2:
            owner = None

        if owner is None and agreement_id is None and job_id is None:
            msg = f'You have to specify one of agreementId, jobId or owner'
            logger.error(msg)
            return jsonify(error=msg), 400
        logger.debug("Try to start")
        api_response = get_sql_status(agreement_id, job_id, owner)
        return jsonify(api_response), 200

    except ApiException as e:
        msg = f'Error getting the status: {e}'
        logger.error(msg)
        return jsonify(error=msg), 400

@services.route('/runningjobs', methods=['GET'])
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
        return jsonify(api_response), 200

    except ApiException as e:
        msg = f'Error getting the status: {e}'
        logger.error(msg)
        return jsonify(error=msg), 400
