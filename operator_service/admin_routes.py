import os
import logging

import psycopg2
from flask import Blueprint, jsonify, request, Response
from kubernetes.client.rest import ApiException

from operator_service.config import Config
from operator_service.kubernetes_api import KubeAPI

adminpg_services = Blueprint("adminpg_services", __name__)
admin_services = Blueprint("admin_services", __name__)


config = Config()
logger = logging.getLogger(__name__)


@adminpg_services.route("/pgsqlinit", methods=["POST"])
def init_pgsql_compute():
    """
    Init pgsql database
    ---
    tags:
      - operation
    consumes:
      - application/json
    """
    output = ""
    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            database=os.getenv("POSTGRES_DB"),
        )
        cursor = connection.cursor()
        create_table_query = """
            CREATE TABLE IF NOT EXISTS jobs
                (agreementId           varchar(255) NOT NULL,
                workflowId         varchar(255) NOT NULL,
                owner         varchar(255),
                status  int,
                statusText varchar(255),
                laststatusupdate timestamp without time zone default NOW(),
                dateCreated timestamp without time zone default NOW(),
                dateFinished timestamp without time zone default NULL,
                configlogURL text,
                publishlogURL text,
                algologURL text,
                outputsURL text,
                ddo text,
                namespace varchar(255),
                stopreq smallint default 0,
                removed smallint default 0,
                workflow text,
                provider varchar(255)
            );
        """
        cursor.execute(create_table_query)
        create_index_query = """CREATE unique INDEX IF NOT EXISTS uniq_agreementId_workflowId ON jobs (agreementId,workflowId)"""
        cursor.execute(create_index_query)
        # create envs tabls
        create_table_query = """
            CREATE TABLE IF NOT EXISTS envs
                (namespace           varchar(255) NOT NULL,
                status         text,
                lastping timestamp without time zone default NOW()
            );
        """
        cursor.execute(create_table_query)
        create_index_query = (
            """CREATE unique INDEX IF NOT EXISTS unique_namespace ON envs (namespace)"""
        )
        cursor.execute(create_index_query)
        # create announce function
        create_table_query = """
        CREATE OR REPLACE FUNCTION announce(environment varchar(255), fullstatus text, lmt int)
          RETURNS TABLE (workflow varchar(255))
          LANGUAGE plpgsql
          AS $function$
          BEGIN
            INSERT INTO envs(namespace, status, lastping) VALUES(environment,fullstatus,NOW()) ON CONFLICT (namespace) DO UPDATE SET status = EXCLUDED.status, lastping = EXCLUDED.lastping;
            RETURN QUERY
            SELECT workflowid FROM jobs WHERE namespace=environment AND status=1 LIMIT lmt;
          END
        $function$;
        """
        cursor.execute(create_table_query)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        output = output + "Error PostgreSQL:" + str(error)

    # add more columns with alter, to insure backwards compat
    try:
        cursor = connection.cursor()
        table_query = "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS did varchar(255)"
        cursor.execute(table_query)
    except (Exception, psycopg2.Error) as error:
        output = output + "Error PostgreSQL:" + str(error)
    # add more columns with alter, to insure backwards compat
    try:
        cursor = connection.cursor()
        table_query = "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS chainid varchar(255)"
        cursor.execute(table_query)
    except (Exception, psycopg2.Error) as error:
        output = output + "Error PostgreSQL:" + str(error)

    # add more columns with alter, to insure backwards compat
    try:
        cursor = connection.cursor()
        table_query = "CREATE INDEX IF NOT EXISTS indx_owner_jobs ON jobs(owner)"
        cursor.execute(table_query)
    except (Exception, psycopg2.Error) as error:
        output = output + "Error PostgreSQL:" + str(error)

    if connection and cursor:
        cursor.close()
        connection.close()
    return output, 200


@admin_services.route("/info", methods=["GET"])
def get_compute_job_info():
    """
    Get info for an job id.
    ---
    tags:
      - operation
    consumes:
      - application/json
    parameters:
      - name: jobId
        in: query
        description: Id of the job.
        required: true
        type: string
    """
    try:
        job_id = request.args["jobId"]
        api_response = KubeAPI(config).get_namespaced_custom_object(job_id)
        logger.info(api_response)
        return jsonify(api_response), 200
    except ApiException as e:
        logger.error(f"The jobId {job_id} is not registered in your namespace: {e}")
        return f"The jobId {job_id} is not registered in your namespace.", 400


@admin_services.route("/list", methods=["GET"])
def list_compute_jobs():
    """
    List all the compute jobs.
    ---
    tags:
      - operation
    consumes:
      - application/json
    """
    try:
        api_response = KubeAPI(config).list_namespaced_custom_object()
        result = list()
        for i in api_response["items"]:
            result.append(i["metadata"]["name"])
        logger.info(api_response)
        return jsonify(result), 200

    except ApiException as e:
        logger.error(
            f"Exception when calling CustomObjectsApi->list_cluster_custom_object: {e}"
        )
        return "Error listing workflows", 400


@admin_services.route("/logs", methods=["GET"])
def get_logs():
    """
    Get the logs for an job id.
    ---
    tags:
      - operation
    consumes:
      - text/plain
    parameters:
      - name: jobId
        in: query
        description: Id of the job.
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
    kube_api = KubeAPI(config)
    try:
        job_id = data.get("jobId")
        component = data.get("component")
        # First we need to get the name of the pods
        label_selector = f"workflow={job_id},component={component}"
        logger.debug(
            f"Looking pods in ns {kube_api.namespace} with labels {label_selector}"
        )
        pod_response = kube_api.list_namespaced_pod(label_selector=label_selector)
    except ApiException as e:
        logger.error(
            f"Exception when calling CustomObjectsApi->list_namespaced_pod: {e}"
        )
        return "Error getting the logs", 400

    try:
        pod_name = pod_response.items[0].metadata.name
        logger.debug(f"pods found: {pod_response}")
    except IndexError as e:
        logger.warning(
            f"Exception getting information about the pod with labels {label_selector}."
            f" Probably pod does not exist: {e}"
        )
        return f"Pod with workflow={job_id} and component={component} not found", 404

    try:
        logger.debug(
            f"looking logs for pod {pod_name} in namespace {kube_api.namespace}"
        )
        logs_response = kube_api.read_namespaced_pod_log(name=pod_name)
        r = Response(response=logs_response, status=200, mimetype="text/plain")
        r.headers["Content-Type"] = "text/plain; charset=utf-8"
        return r

    except ApiException as e:
        logger.error(
            f"Exception when calling CustomObjectsApi->read_namespaced_pod_log: {e}"
        )
        return "Error getting the logs", 400
