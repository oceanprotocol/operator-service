import logging

import kubernetes
from flask import Blueprint
from kubernetes.client.rest import ApiException

services = Blueprint('services', __name__)


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
    # Configure API key authorization: BearerToken
    configuration = kubernetes.client.Configuration()
    configuration.api_key['authorization'] = 'YOUR_API_KEY'
    api_instance = kubernetes.client.ApiextensionsV1beta1Api(
        kubernetes.client.ApiClient(configuration))
    body = kubernetes.client.V1beta1CustomResourceDefinition()
    try:
        api_response = api_instance.create_custom_resource_definition(body)
        logging.info(api_response)
    except ApiException as e:
        print(
            "Exception when calling ApiextensionsV1beta1Api->create_custom_resource_definition: "
            "%s\n" % e)

    return 'Hello', 200


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
    return 'Successfully delete', 200
