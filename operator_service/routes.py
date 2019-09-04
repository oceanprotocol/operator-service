import logging
import uuid
from configparser import ConfigParser
from os import path

import kubernetes
import yaml
from flask import Blueprint, jsonify, request, Response
from kubernetes import client, config
from kubernetes.client.rest import ApiException

services = Blueprint('services', __name__)

# Configuration to connect to k8s.
if not path.exists('/.dockerenv'):
    config.load_kube_config()
else:
    config.load_incluster_config()

# create instances of the API classes
api_customobject = client.CustomObjectsApi()
api_core = client.CoreV1Api()


config_parser = ConfigParser()
configuration = config_parser.read('/operator-service/config.ini')
group = config_parser.get('resources', 'group')  # str | The custom resource's group name
version = config_parser.get('resources', 'version')  # str | The custom resource's version
namespace = config_parser.get('resources', 'namespace')  # str | The custom resource's namespace
plural = config_parser.get('resources',
                           'plural')  # str | The custom resource's plural name. For TPRs this


# would be


@services.route('/init', methods=['POST'])
def init_execution():
    """
    Initialize the execution when someone call to the execute endpoint in brizo.
    ---
    tags:
      - operation
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: Init workflow.
        schema:
          type: object
          required:
            - serviceAgreementId
            - workflow
          properties:
            serviceAgreementId:
              description: Identifier of the service agreement.
              type: string
              example: 'bb23s87856d59867503f80a690357406857698570b964ac8dcc9d86da4ada010'
            workflow:
              description: Workflow definition.
              type: dictionary
              example: {"@context": "https://w3id.org/future-method/v1",
                        "authentication": [],
                        "created": "2019-04-09T19:02:11Z",
                        "id": "did:op:bda17c126f5a411c8edd94cd0700e466a860f269a0324b77ae37d04cf84bb894",
                        "proof": {
                          "created": "2019-04-09T19:02:11Z",
                          "creator": "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e",
                          "signatureValue": "1cd57300733bcbcda0beb59b3e076de6419c0d7674e7befb77820b53c79e3aa8f1776effc64cf088bad8cb694cc4d71ebd74a13b2f75893df5a53f3f318f6cf828",
                          "type": "DDOIntegritySignature"
                        },
                        "publicKey": [
                          {
                            "id": "did:op:60000f48357a42fbb8d6ff3a25a23413e9cc852db091485eb89506a5fed9f33c",
                            "owner": "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e",
                            "type": "EthereumECDSAKey"
                          }
                        ],
                        "service": [
                          {
                            "index": "0",
                            "serviceEndpoint": "https://brizo.nile.dev-ocean.com/api/v1/aquarius/assets/ddo/{did}",
                            "type": "Metadata",
                            "attributes": {
                              "main": {
                                "dateCreated": "2012-10-10T17:00:00Z",
                                "type": "workflow",
                                "datePublished": "2019-04-09T19:02:11Z"
                              },
                              "workflow": {
                                "stages": [
                                  {
                                    "index": 0,
                                    "stageType": "Filtering",
                                    "requirements": {
                                      "serverInstances": 1,
                                      "container": {
                                        "image": "openjdk",
                                        "tag": "14-jdk",
                                        "checksum": "sha256:cb57ecfa6ebbefd8ffc7f75c0f00e57a7fa739578a429b6f72a0df19315deadc"
                                      }
                                    },
                                    "input": [
                                      {
                                        "index": 0,
                                        "id": "did:op:c0ea298bcd5d4140a207655528ded5fb44620d9765f84f7096f27efcf0832afc"
                                      },
                                      {
                                        "index": 1,
                                        "id": "did:op:63301ee7ed4d4430b753f1b90d2f890103d9edf556814e268d34f58de800ac52"
                                      }
                                    ],
                                    "transformation": {
                                      "id": "did:op:49ce7de0056e4d829d9de8c1f78911f9be34645483354d9c899325de07343561"
                                    },
                                    "output": {
                                      "metadataUrl": "https://aquarius.marketplace.dev-ocean.com",
                                      "secretStoreUrl": "https://secret-store.nile.dev-ocean.com",
                                      "accessProxyUrl": "https://brizo.marketplace.dev-ocean.com",
                                      "brizoAddress": "0x4aaab179035dc57b35e2ce066919048686f82972",
                                      "metadata": {
                                        "name": "Workflow output"
                                      }
                                    }
                                  }
                                ]
                              }
                            }
                          }
                        ]
                      }

    response:
      201:
        description: Workflow inited successfully.
      400:
        description: Some error
    """
    execution_id = generate_new_id()
    body = create_execution(request.json['workflow'], execution_id)
    try:
        api_response = api_customobject.create_namespaced_custom_object(group, version, namespace,
                                                                        plural, body)
        logging.info(api_response)
        return execution_id, 200

    except ApiException as e:
        logging.error(
            f'Exception when calling CustomObjectsApi->create_namespaced_custom_object: {e}')
        return 'Workflow could not start', 400


@services.route('/stop', methods=['DELETE'])
def stop_execution():
    """
    Stop the current workflow execution.
    ---
    tags:
      - operation
    consumes:
      - application/json
    parameters:
      - name: executionId
    """
    name = request.args['executionId']  # str | the custom object's name
    body = kubernetes.client.V1DeleteOptions()  # V1DeleteOptions |
    grace_period_seconds = 56  # int | The duration in seconds before the object should be
    # deleted. Value must be non-negative integer. The value zero indicates delete immediately.
    # If this value is nil, the default grace period for the specified type will be used.
    # Defaults to a per object value if not specified. zero means delete immediately. (optional)
    orphan_dependents = True  # bool | Deprecated: please use the PropagationPolicy, this field
    # will be deprecated in 1.7. Should the dependent objects be orphaned. If true/false,
    # the \"orphan\" finalizer will be added to/removed from the object's finalizers list. Either
    # this field or PropagationPolicy may be set, but not both. (optional)
    propagation_policy = 'propagation_policy_example'  # str | Whether and how garbage collection
    # will be performed. Either this field or OrphanDependents may be set, but not both. The
    # default policy is decided by the existing finalizer set in the metadata.finalizers and the
    # resource-specific default policy. (optional)

    try:
        api_response = api_customobject.delete_namespaced_custom_object(group, version, namespace,
                                                                        plural, name, body,
                                                                        grace_period_seconds=grace_period_seconds,
                                                                        orphan_dependents=orphan_dependents,
                                                                        propagation_policy=propagation_policy)
        logging.info(api_response)
    except ApiException as e:
        print("Exception when calling CustomObjectsApi->delete_namespaced_custom_object: %s\n" % e)
    return 'Successfully delete', 200


@services.route('/info/<execution_id>', methods=['GET'])
def get_execution_info(execution_id):
    """
    Get info for an execution id.
    ---
    tags:
      - operation
    consumes:
      - application/json
    parameters:
      - name: executionId
        in: path
        description: Id of the execution.
        required: true
        type: string
    """
    try:
        api_response = api_customobject.get_namespaced_custom_object(group, version, namespace, plural,
                                                                     execution_id)
        logging.info(api_response)
        return yaml.dump(api_response), 200
    except ApiException as e:
        logging.error(f'The executionId {execution_id} is not registered in your namespace.')
        return f'The executionId {execution_id} is not registered in your namespace.', 400


@services.route('/list', methods=['GET'])
def list_executions():
    """
    List all the execution workflows.
    ---
    tags:
      - operation
    consumes:
      - application/json
    """
    try:
        api_response = api_customobject.list_namespaced_custom_object(group, version, namespace, plural)
        result = list()
        for i in api_response['items']:
            result.append(i['metadata']['name'])
        logging.info(api_response)
        return jsonify(result), 200

    except ApiException as e:
        logging.error(
            f'Exception when calling CustomObjectsApi->list_cluster_custom_object: {e}')
        return 'Error listing workflows', 400


@services.route('/logs', methods=['GET'])
def get_logs():
    """
    Get the logs for an execution id.
    ---
    tags:
      - operation
    consumes:
      - text/plain
    parameters:
      - name: executionId
        in: query
        description: Id of the execution.
        required: true
        type: string
      - name: component
        in: query
        description: Workflow component (config, algorithm, publish)
        required: true
        type: string
    responses:
      200:
        description: Get correctly the logs
      400:
        description: Error consume Kubernetes API
    """
    data = request.args
    required_attributes = [
        'executionId',
        'component'
    ]
    try:
        execution_id = data.get('executionId')
        component = data.get('component')
        # logging.error(f'request:{request}')
        # logging.error(f'data:{data}')
        # First we need to get the name of the pods
        label_selector = f'workflow={execution_id},component={component}'
        logging.error(f'label_selector: {label_selector}')
        pod_response = api_core.list_namespaced_pod(namespace, label_selector=label_selector)
        pod_name = pod_response.items[0].metadata.name
    except ApiException as e:
        logging.error(
            f'Exception when calling CustomObjectsApi->list_namespaced_pod: {e}')
        return 'Error getting the logs', 400

    try:
        logs_response = api_core.read_namespaced_pod_log(name=pod_name, namespace=namespace)
        r = Response(response=logs_response, status=200, mimetype="text/plain")
        r.headers["Content-Type"] = "text/plain; charset=utf-8"
        return r

    except ApiException as e:
        logging.error(
            f'Exception when calling CustomObjectsApi->read_namespaced_pod_log: {e}')
        return 'Error getting the logs', 400


def create_execution(workflow, execution_id):
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


# TODO Use the commons utils library to do this when we set up the project.
def generate_new_id():
    """
    Generate a new id without prefix.

    :return: Id, str
    """
    return uuid.uuid4().hex
