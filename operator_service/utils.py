import uuid
import logging

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
    assert isinstance(data, dict), 'invalid payload format.'
    logger.info('got %s request: %s' % (method, data))
    if not data:
        logger.error('%s request failed: data is empty.' % method)
        return 'payload seems empty.', 400

    for attr in required_attributes:
        if attr not in data:
            logger.error('%s request failed: required attr %s missing.' % (method, attr))
            return '"%s" is required in the call to %s' % (attr, method), 400

    return None, None


def verify_signature(keeper, signature, original_msg, allowed_addresses):
    address = keeper.personal_ec_recover(original_msg, signature)
    if address.lower() in allowed_addresses:
        return

    msg = f'Invalid signature {signature} of documentId {original_msg},' \
          f'the signing ethereum account {address} is not authorized to use this service.'
    raise InvalidSignatureError(msg)


def get_list_of_allowed_providers():
    try:
        config_allowed_list=json.loads(os.getenv("ALLOWEDPROVIDERS"))
        if not isinstance(config_allowed_list,list):
            logger.error('Failed loading ALLOWEDPROVIDERS')
            return []
        return config_allowed_list
    except ApiException as e:
        logging.error(f'Exception when calling json.loads(os.getenv("ALLOWEDPROVIDERS")): {e}')
        return []

def get_compute_resources(agreement_id):
    resources=dict()
    resources['inputVolumesize']="1Gi"
    resources['outputVolumesize']="1Gi"
    resources['adminlogsVolumesize']="1Gi"
    resources['requests_cpu']="1"
    resources['requests_memory']="200Mi"
    resources['limits_cpu']="2"
    resources['limits_memory']="500Mi"
    return(resources)
    