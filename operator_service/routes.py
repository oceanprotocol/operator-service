import logging
from configparser import ConfigParser

import kubernetes
import yaml
from flask import Blueprint
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
def init_workflow():
    """
    Initialize the worker when someone call to the execute endpoint in brizo.
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
            - serviceDefinitionId
            - workflow
          properties:
            serviceAgreementId:
              description: Identifier of the service agreement.
              type: string
              example: 'bb23s87856d59867503f80a690357406857698570b964ac8dcc9d86da4ada010'
            workflow:
              description: Workflow definition.
              type: dictionary
              example: {"stages": [{
          "index": 0,
          "stageType": "Filtering",
          "requirements": {
            "computeServiceId": "did:op8934894328989423",
            "serviceDefinitionId": "1",
            "serverId": "1",
            "serverInstances": 1,
            "container": {
              "image": "tensorflow/tensorflow",
              "tag": "latest",
              "checksum": "sha256:cb57ecfa6ebbefd8ffc7f75c0f00e57a7fa739578a429b6f72a0df19315deadc"
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
            "computeServiceId": "did:op8934894328989423",
            "serviceDefinitionId": "1",
            "serverId": "2",
            "serverInstances": 1,
            "container": {
              "image": "tensorflow/tensorflow",
              "tag": "latest",
              "checksum": "sha256:cb57ecfa6ebbefd8ffc7f75c0f00e57a7fa739578a429b6f72a0df19315deadc"
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
        }]}
    response:
      201:
        description: Workflow inited successfully.
      400:
        description: Some error
    """
    with open('operator_service/workflow.yaml', 'r') as stream:
        body = yaml.safe_load(stream)
    body['apiVersion'] = group + '/' + version
    try:
        api_response = api_instance.create_namespaced_custom_object(group, version, namespace,
                                                                    plural, body)
        logging.info(api_response)
        return yaml.dump(api_response), 200

    except ApiException as e:
        logging.error(
            f'Exception when calling CustomObjectsApi->create_namespaced_custom_object: {e}')
        return 'Workflow could not start', 400


@services.route('/stop', methods=['DELETE'])
def stop_workflow():
    """
    Stop the current workflow.
    ---
    tags:
      - operation
    consumes:
      - application/json
    parameters:
      - name: serviceDefinitionId
    """
    name = 'workflow-1'  # str | the custom object's name
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


@services.route('/list', methods=['GET'])
def list_workflows():
    """
    List all the workflows.
    ---
    tags:
      - operation
    consumes:
      - application/json
    """
    try:
        api_response = api_instance.list_cluster_custom_object(group, version, plural)

        logging.info(api_response)
        return yaml.dump(api_response), 200

    except ApiException as e:
        logging.error(
            f'Exception when calling CustomObjectsApi->list_cluster_custom_object: {e}')
        return 'Error listing workflows', 400
