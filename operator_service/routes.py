import logging
import uuid
from configparser import ConfigParser

import kubernetes
import yaml
from flask import Blueprint, jsonify, request
from kubernetes import client, config
from kubernetes.client.rest import ApiException

services = Blueprint('services', __name__)

# Configuration to connect to k8s.
config.load_kube_config()
# create an instance of the API class
api_instance = client.CustomObjectsApi()

config_parser = ConfigParser()
configuration = config_parser.read('config.ini')
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
                        "id":
                        "did:op:8d1b4d73e7af4634958f071ab8dfe7ab0df14019755e444090fd392c8ec9c3f4",
                        "proof": {
                            "created": "2019-04-09T19:02:11Z",
                            "creator": "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e",
                            "signatureValue":
                            "1cd57300733bcbcda0beb59b3e076de6419c0d7674e7befb77820b53c79e3aa8f1776effc64cf088bad8cb694cc4d71ebd74a13b2f75893df5a53f3f318f6cf828",
                            "type": "DDOIntegritySignature"
                        },
                        "publicKey": [{
                            "id":
                            "did:op:8d1b4d73e7af4634958f071ab8dfe7ab0df14019755e444090fd392c8ec9c3f4",
                            "owner": "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e",
                            "type": "EthereumECDSAKey"
                        }],
                        "service":[{
                            "index" : 0,
                            "serviceEndpoint":
                            "http://172.15.0.15:5000/api/v1/aquarius/assets/ddo/did:op
                            :8d1b4d73e7af4634958f071ab8dfe7ab0df14019755e444090fd392c8ec9c3f4",
                            "type": "metadata",
                            "attributes": {
                                "main": {
                                    "dateCreated": "2012-10-10T17:00:00Z",
                                    "type": "workflow",
                                    "datePublished": "2019-04-09T19:02:11Z",
                                    "workflow": {
                                        "stages": [{
                                          "index": 0,
                                          "stageType": "Filtering",
                                          "requirements": {
                                            "serverInstances": 1,
                                            "container": {
                                              "image": "tensorflow/tensorflow",
                                              "tag": "latest",
                                              "checksum":
                                              "sha256:cb57ecfa6ebbefd8ffc7f75c0f00e57a7fa739578a429b6f72a0df19315deadc"
                                            }
                                          },
                                          "input": [{
                                            "index": 0,
                                            "id": "did:op:12345"
                                          }, {
                                            "index": 1,
                                            "id": "did:op:67890"
                                          }
                                          ],
                                          "transformation": {
                                            "id": "did:op:abcde"
                                          },
                                          "output": {}
                                        }, {
                                          "index": 1,
                                          "stageType": "Transformation",
                                          "requirements": {
                                            "serverInstances": 1,
                                            "container": {
                                              "image": "tensorflow/tensorflow",
                                              "tag": "latest",
                                              "checksum":
                                              "sha256:cb57ecfa6ebbefd8ffc7f75c0f00e57a7fa739578a429b6f72a0df19315deadc"
                                            }
                                          },
                                          "input": [{
                                            "index": 0,
                                            "previousStage": 0
                                          }],
                                          "transformation": {
                                            "id": "did:op:999999"
                                          },
                                          "output": {}
                                        }]
                                      }
                                }}
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
        api_response = api_instance.create_namespaced_custom_object(group, version, namespace,
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
        api_response = api_instance.delete_namespaced_custom_object(group, version, namespace,
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
        api_response = api_instance.get_namespaced_custom_object(group, version, namespace, plural,
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
        api_response = api_instance.list_cluster_custom_object(group, version, plural)
        result = list()
        for i in api_response['items']:
            result.append(i['metadata']['name'])
        logging.info(api_response)
        return jsonify(result), 200

    except ApiException as e:
        logging.error(
            f'Exception when calling CustomObjectsApi->list_cluster_custom_object: {e}')
        return 'Error listing workflows', 400


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
