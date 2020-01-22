import logging
import uuid
from configparser import ConfigParser
from os import path

import kubernetes
import os
import psycopg2
import yaml
from flask import Blueprint, jsonify, request, Response
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import simplejson as json
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
                           'plural')  # str | The custom resource's plural name. For TPRs this would be



@services.route('/compute', methods=['POST'])
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
        required: false
        description: Init workflow.
        schema:
          workflow:
          nullable: true
          example: {
                          "agreementId":"0xACBd138aBD70e2F00903268F3Db08f2D25677C9e",
                          "owner":"0xC41808BBef371AD5CFc76466dDF9dEe228d2BdAA",
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
                                  "brizoUrl": "https://brizo.marketplace.dev-ocean.com",
                                  "brizoAddress": "0x4aaab179035dc57b35e2ce066919048686f82972",
                                  "metadata": {
                                      "name": "Workflow output"
                                  },
                                  "metadataUrl": "https://aquarius.marketplace.dev-ocean.com",
                                  "secretStoreUrl": "https://secret-store.nile.dev-ocean.com",
                                  "whitelist": [
                                      "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e",
                                      "0xACBd138aBD70e2F00903268F3Db08f2D25677C9e"
                                  ],
                                  "owner":"0xC41808BBef371AD5CFc76466dDF9dEe228d2BdAA",
                                  "publishoutput":true,
                                  "publishalgolog":true
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
    if 'agreementId' not in request.json:
        logging.error(f'Missing agreementId')
        return 'Missing agreementId', 400
    if 'owner' not in request.json:
        logging.error(f'Missing ownerId')
        return 'Missing ownerId', 400
    if 'stages' not in request.json:
        logging.error(f'Missing stages')
        return 'Missing stages', 400 
    if not request.json['stages']:
        logging.error(f'Missing stages')
        return 'Missing stages', 400 
    if 'algorithm' not in request.json['stages'][0]:
        logging.error(f'Missing algorithm in stage')
        return 'Missing algorithm in stages', 400
    if 'compute' not in request.json['stages'][0]:
        logging.error(f'Missing compute in stage')
        return 'Missing compute in stages', 400
    if 'input' not in request.json['stages'][0]:
        logging.error(f'Missing input in stage')
        return 'Missing input in stages', 400
    if 'output' not in request.json['stages'][0]:
        logging.error(f'Missing output in stage')
        return 'Missing output in', 400
    agreementId=request.json['agreementId']
    owner=request.json['owner']
    execution_id = generate_new_id()
    logging.error(f'Got execution_id: {execution_id}')
    body = create_execution(request.json, execution_id)
    logging.error(f'Got body: {body}')
    try:
        api_response = api_customobject.create_namespaced_custom_object(group, version, namespace,
                                                                        plural, body)
        logging.info(api_response)
        create_sql_job(agreementId,str(execution_id),owner)
        status_list = get_sql_status(agreementId,str(execution_id),owner)
        return jsonify(status_list), 200
    except ApiException as e:
        logging.error(f'Exception when calling CustomObjectsApi->create_namespaced_custom_object: {e}')
        return 'Unable to create job', 400


@services.route('/compute', methods=['PUT'])
def stop_execution():
    """
    Stop the current workflow execution.
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
        description: Id of the execution.
        type: string
      - name: owner
        in: query
        description: owner
        type: string
    """
    try:
      if 'agreementId' not in request.args:
        agreementId = None
      elif len(request.args['agreementId'])<2:
        agreementId = None
      else:
        agreementId = request.args['agreementId']
      if 'jobId' not in request.args:
        jobId = None
      elif len(request.args['jobId'])<2:
        jobId = None
      else:
        jobId = request.args['jobId']
      if 'owner' not in request.args:
        owner = None
      elif len(request.args['owner'])<2:
        owner = None
      else:
        owner = request.args['owner']
      if owner is None and agreementId is None and jobId is None:
        logging.error(f'All args are null ?')
        return f'You have to specify one of agreementId,jobId or owner', 400    
      else:
        jobslist=get_sql_jobs(agreementId,jobId,owner)
        for ajob in jobslist:
            name=ajob
            logging.info(f'Stoping job : {name}')
            stop_sql_job(name)
        status_list = get_sql_status(agreementId,jobId,owner)
        return jsonify(status_list), 200
    except ApiException as e:
        print("Exception when calling CustomObjectsApi->delete_namespaced_custom_object: %s\n" % e)
        return 'Error stopping job', 400


@services.route('/compute', methods=['DELETE'])
def delete_execution():
    """
    Deletes the current workflow execution.
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
        description: Id of the execution.
        type: string
      - name: owner
        in: query
        description: owner
        type: string
    """
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
        if 'agreementId' not in request.args:
          agreementId = None
        elif len(request.args['agreementId'])<2:
          agreementId = None
        else:
          agreementId = request.args['agreementId']
        if 'jobId' not in request.args:
          jobId = None
        elif len(request.args['jobId'])<2:
          jobId = None
        else:
          jobId = request.args['jobId']
        if 'owner' not in request.args:
          owner = None
        elif len(request.args['owner'])<2:
          owner = None
        else:
          owner = request.args['owner']
        if owner is None and agreementId is None and jobId is None:
          logging.error(f'All args are null ?')
          return f'You have to specify one of agreementId,jobId or owner', 400    
        else:
          jobslist=get_sql_jobs(agreementId,jobId,owner)
          for ajob in jobslist:
              name=ajob
              logging.info(f'Deleting job : {name}')
              remove_sql_job(name)
              api_response = api_customobject.delete_namespaced_custom_object(group, version, namespace,
                                                                        plural, name, body,
                                                                        grace_period_seconds=grace_period_seconds,
                                                                        orphan_dependents=orphan_dependents,
                                                                        propagation_policy=propagation_policy)
              logging.info(api_response)
        status_list = get_sql_status(agreementId,jobId,owner)
        return jsonify(status_list), 200
    except ApiException as e:
        logging.error(f'Exception when calling CustomObjectsApi->delete_namespaced_custom_object: {e}')
        return 'Error deleteing job', 400
        



@services.route('/compute', methods=['GET'])
def get_execution_status():
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
        description: Id of the execution.
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
      if 'agreementId' not in request.args:
        agreementId = None
      elif len(request.args['agreementId'])<2:
        agreementId = None
      else:
        agreementId = request.args['agreementId']
      if 'jobId' not in request.args:
        jobId = None
      elif len(request.args['jobId'])<2:
        jobId = None
      else:
        jobId = request.args['jobId']
      if 'owner' not in request.args:
        owner = None
      elif len(request.args['owner'])<2:
        owner = None
      else:
        owner = request.args['owner']
      if owner is None and agreementId is None and jobId is None:
        logging.error(f'All args are null ?')
        return f'You have to specify one of agreementId,jobId or owner', 400    
      else:
        logging.error("Try to start")
        api_response = get_sql_status(agreementId,jobId,owner)
       # logging.error(f'Got from sql: {api_response}')
        return jsonify(api_response), 200
    except ApiException as e:
        logging.error(
            f'Exception when calling status: {e}')
        return 'Error getting the status', 400
    

# methhods not in API.md - admin only

@services.route('/pgsqlinit', methods=['POST'])
def init_pgsqlexecution():
    """
    Init pgsql database
    ---
    tags:
      - operation
    consumes:
      - application/json
    """
    output = ""
    try:
      connection = psycopg2.connect(user = os.getenv("POSTGRES_USER"),
                                  password = os.getenv("POSTGRES_PASSWORD"),
                                  host = os.getenv("POSTGRES_HOST"),
                                  port = os.getenv("POSTGRES_PORT"),
                                  database = os.getenv("POSTGRES_DB"))
      cursor = connection.cursor()
      create_table_query = '''CREATE TABLE IF NOT EXISTS jobs 
          (agreementId           varchar(255) NOT NULL,
          workflowId         varchar(255) NOT NULL,
          owner         varchar(255),
          status  int,
          statusText varchar(255),
          dateCreated timestamp without time zone default NOW(),
          dateFinished timestamp without time zone default NULL,
          configlogURL text,
          publishlogURL text,
          algologURL text,
          outputsURL text,
          ddo text,
          namespace varchar(255),
          stopreq smallint default 0,
          removed smallint default 0
          ); '''
      cursor.execute(create_table_query)
      #queries below are for upgrade purposes
      create_table_query = '''ALTER TABLE jobs ADD COLUMN IF NOT EXISTS namespace varchar(255)'''
      cursor.execute(create_table_query)
      create_table_query = '''ALTER TABLE jobs ADD COLUMN IF NOT EXISTS stopreq smallint default 0'''
      cursor.execute(create_table_query)
      create_table_query = '''ALTER TABLE jobs ADD COLUMN IF NOT EXISTS removed smallint default 0'''
      cursor.execute(create_table_query)
      create_index_query = '''CREATE unique INDEX IF NOT EXISTS uniq_agreementId_workflowId ON jobs (agreementId,workflowId)'''
      cursor.execute(create_index_query)
      connection.commit()
    except (Exception, psycopg2.Error) as error :
      output = output + "Error PostgreSQL:"+str(error)
    finally:
    #closing database connection.
        if(connection):
            cursor.close()
            connection.close()
    
    return output, 200




@services.route('/info', methods=['GET'])
def get_execution_info():
    """
    Get info for an execution id.
    ---
    tags:
      - operation
    consumes:
      - application/json
    parameters:
      - name: jobId
        in: query
        description: Id of the execution.
        required: true
        type: string
    """
    try:
        execution_id = request.args['jobId']
        api_response = api_customobject.get_namespaced_custom_object(group, version, namespace, plural,
                                                                     execution_id)
        logging.info(api_response)
        return jsonify(api_response), 200
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
      - name: jobId
        in: query
        description: Id of the execution.
        required: true
        type: string
      - name: component
        in: query
        description: Workflow component (configure, algorithm, publish)
        required: true
        type: string
    responses:
      200:
        description: Get correctly the logs
      400:
        description: Error consume Kubernetes API
      404:
        description: Pod not found for the given parameters
    """
    data = request.args
    required_attributes = [
        'jobId',
        'component'
    ]
    try:
        execution_id = data.get('jobId')
        component = data.get('component')
        # First we need to get the name of the pods
        label_selector = f'workflow={execution_id},component={component}'
        logging.debug(f'Looking pods in ns {namespace} with labels {label_selector}')
        pod_response = api_core.list_namespaced_pod(namespace, label_selector=label_selector)
    except ApiException as e:
        logging.error(
            f'Exception when calling CustomObjectsApi->list_namespaced_pod: {e}')
        return 'Error getting the logs', 400

    try:
        pod_name = pod_response.items[0].metadata.name
        logging.debug(f'pods found: {pod_response}')
    except IndexError as e:
        logging.warning(f'Exception getting information about the pod with labels {label_selector}.'
                        f' Probably pod does not exist')
        return f'Pod with workflow={execution_id} and component={component} not found', 404

    try:
        logging.debug(f'looking logs for pod {pod_name} in namespace {namespace}')
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


#sql handlers


def get_sql_status(agreementId,jobId,owner):
  result = []
  #enforce strings
  logging.error("Start get_sql_status\n")
  connection = getpgconn()
  try:
      cursor = connection.cursor()
      logging.error("Connected\n")
      params= dict()
      select_query="SELECT agreementId,workflowId,owner,status,statusText,extract(epoch from dateCreated) as dateCreated,extract(epoch from dateFinished) as dateFinished,configlogURL,publishlogURL,algologURL,outputsURL,ddo,stopreq,removed FROM jobs WHERE 1=1"
      if agreementId is not None:
        select_query=select_query+" AND agreementId=%(agreementId)s"
        params['agreementId']=str(agreementId)
      if jobId is not None:
        select_query=select_query+" AND workflowId=%(jobId)s"
        params['jobId']=str(jobId)
      if owner is not None:
        select_query=select_query+" AND owner=%(owner)s"
        params['owner']=str(owner)
      logging.error(f'Got select_query: {select_query}')
      logging.error(f'Got params: {params}')
      cursor.execute(select_query, params)
      while True:
        temprow=dict()
        row = cursor.fetchone()
        if row == None:
            break
        temprow['agreementId']=row[0]
        temprow['jobId']=row[1]
        temprow['owner']=row[2]
        temprow['status']=row[3]
        temprow['statusText']=row[4]
        temprow['dateCreated']=row[5]
        temprow['dateFinished']=row[6]
        #temprow['configlogUrl']=row[7]
        #temprow['publishlogUrl']=row[8]
        temprow['algologUrl']=row[9]
        temprow['outputsUrl']=row[10]
        temprow['ddo']=''
        temprow['did']=''
        if row[11] is not None:
            temprow['ddo']=str(row[11])
            ddo_json = json.loads(temprow['ddo'])
            if 'id' in ddo_json:
                temprow['did']=ddo_json['id']
        temprow['stopreq']=row[12]
        temprow['removed']=row[13]
        result.append(temprow)
        
  except (Exception, psycopg2.Error) as error :
        result=dict()
        logging.error(f'Got PG error in get_sql_status: {error}')
  finally:
    #closing database connection.
        if(connection):
            cursor.close()
            connection.close()
        logging.error('Done')
  return result


def get_sql_jobs(agreementId,jobId,owner):
  result = []
  logging.error("Start get_sql_status\n")
  connection = getpgconn()
  try:
      cursor = connection.cursor()
      logging.error("Connected\n")
      params=dict()
      select_query="SELECT workflowId FROM jobs WHERE 1=1"
      if agreementId is not None:
        select_query=select_query+" AND agreementId=%(agreementId)s"
        params['agreementId']=str(agreementId)
      if jobId is not None:
        select_query=select_query+" AND workflowId=%(jobId)s"
        params['jobId']=str(jobId)
      if owner is not None:
        select_query=select_query+" AND owner=%(owner)s"
        params['owner']=str(owner)
      logging.error(f'Got select_query: {select_query}')
      logging.error(f'Got params: {params}')
      cursor.execute(select_query, params)
      temprow=dict()
      while True:
        row = cursor.fetchone()
        if row == None:
            break
        result.append(row[0])
  except (Exception, psycopg2.Error) as error :
        result=dict()
        logging.error(f'Got PG error in get_sql_jobs: {error}')
  finally:
    #closing database connection.
        if(connection):
            cursor.close()
            connection.close()
        logging.error('Done')
  return result


def create_sql_job(agreementId,jobId,owner):
    connection = getpgconn()
    try:
      cursor = connection.cursor()
      postgres_insert_query = """ INSERT INTO jobs (agreementId,workflowId,owner,status,statusText) VALUES (%s,%s,%s,%s,%s)"""
      record_to_insert = (str(agreementId),str(jobId),str(owner),10,"Job started")
      cursor.execute(postgres_insert_query, record_to_insert)
      connection.commit()
    except (Exception, psycopg2.Error) as error :
       logging.error(f'Got PG error in create_sql_job: {error}')
    finally:
    #closing database connection.
        if(connection):
            cursor.close()
            connection.close()


def stop_sql_job(execution_id):
    connection = getpgconn()
    try:
      cursor = connection.cursor()
      postgres_insert_query = """ UPDATE jobs SET stopreq=1 WHERE workflowId=%s"""
      record_to_insert = (str(execution_id),)
      cursor.execute(postgres_insert_query, record_to_insert)
      connection.commit()
    except (Exception, psycopg2.Error) as error :
       logging.error(f'Got PG error in stop_sql_job: {error}')
    finally:
    #closing database connection.
        if(connection):
            cursor.close()
            connection.close()

def remove_sql_job(execution_id):
    connection = getpgconn()
    try:
      cursor = connection.cursor()
      postgres_insert_query = """ UPDATE jobs SET removed=1 WHERE workflowId=%s"""
      record_to_insert = (str(execution_id),)
      cursor.execute(postgres_insert_query, record_to_insert)
      connection.commit()
    except (Exception, psycopg2.Error) as error :
       logging.error(f'Got PG error in remove_sql_job: {error}')
    finally:
    #closing database connection.
        if(connection):
            cursor.close()
            connection.close()            

def getpgconn():
    try:
        connection = psycopg2.connect(user = os.getenv("POSTGRES_USER"),
                                  password = os.getenv("POSTGRES_PASSWORD"),
                                  host = os.getenv("POSTGRES_HOST"),
                                  port = os.getenv("POSTGRES_PORT"),
                                  database = os.getenv("POSTGRES_DB"))
        connection.set_client_encoding('LATIN9')
        return connection
    except (Exception, psycopg2.Error) as error :
        logging.error(f'New PG connect error: {error}')
        return None

