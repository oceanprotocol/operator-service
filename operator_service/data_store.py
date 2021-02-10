import os
import logging

import psycopg2
import simplejson as json


def get_sql_status(agreement_id, job_id, owner):
    # enforce strings
    logging.debug("Start get_sql_status\n")
    logging.debug("Connected\n")
    params = dict()
    select_query = '''
    SELECT agreementId, workflowId, owner, status, statusText, 
        extract(epoch from dateCreated) as dateCreated, 
        extract(epoch from dateFinished) as dateFinished,
        configlogURL, publishlogURL, algologURL, outputsURL, ddo, stopreq, removed 
    FROM jobs WHERE 1=1
    '''

    if agreement_id is not None:
        select_query = select_query + " AND agreementId=%(agreementId)s"
        params['agreementId'] = str(agreement_id)

    if job_id is not None:
        select_query = select_query + " AND workflowId=%(jobId)s"
        params['jobId'] = str(job_id)

    if owner is not None:
        select_query = select_query + " AND owner=%(owner)s"
        params['owner'] = str(owner)

    logging.debug(f'Got select_query: {select_query}')
    logging.debug(f'Got params: {params}')

    result = []
    rows = _execute_query(select_query, params, 'get_sql_status', get_rows=True)
    if not rows:
        return result

    for row in rows:
        temprow = dict()
        temprow['agreementId'] = row[0]
        temprow['jobId'] = row[1]
        temprow['owner'] = row[2]
        temprow['status'] = row[3]
        temprow['statusText'] = row[4]
        temprow['dateCreated'] = row[5]
        temprow['dateFinished'] = row[6]
        # temprow['configlogUrl']=row[7]
        # temprow['publishlogUrl']=row[8]
        temprow['algorithmLogUrl'] = row[9]
        temprow['resultsUrl'] = ''
        if row[10] and len(str(row[10])) > 2:
            temprow['resultsUrl'] = json.loads(str(row[10]))
        temprow['resultsDid'] = ''
        if row[11] and len(str(row[11])) > 2:
            ddo_json = json.loads(str(row[11]))
            temprow['resultsDid'] = ddo_json.get('id', '')
        temprow['stopreq'] = row[12]
        temprow['removed'] = row[13]
        result.append(temprow)
    return result


def get_sql_jobs(agreement_id, job_id, owner):
    logging.debug("Start get_sql_status\n")
    logging.debug("Connected\n")
    params = dict()
    select_query = "SELECT workflowId FROM jobs WHERE 1=1"
    if agreement_id is not None:
        select_query = select_query + " AND agreementId=%(agreementId)s"
        params['agreementId'] = str(agreement_id)
    if job_id is not None:
        select_query = select_query + " AND workflowId=%(jobId)s"
        params['jobId'] = str(job_id)
    if owner is not None:
        select_query = select_query + " AND owner=%(owner)s"
        params['owner'] = str(owner)
    logging.debug(f'Got select_query: {select_query}')
    logging.debug(f'Got params: {params}')
    try:
        rows = _execute_query(select_query, params, 'get_sql_jobs', get_rows=True)
        if not rows:
            return []
        return [row[0] for row in rows]
    except (Exception, psycopg2.Error) as error:
        logging.error(f'PG query error: {error}')
        return

def get_sql_running_jobs():
    # enforce strings
    params = dict()
    select_query = '''
    SELECT agreementId, workflowId, owner, status, statusText, 
        extract(epoch from dateCreated) as dateCreated, 
        namespace FROM jobs WHERE dateFinished IS NULL
    '''
    result = []
    rows = _execute_query(select_query, params, 'get_sql_status', get_rows=True)
    if not rows:
        return result
    for row in rows:
        temprow = dict()
        temprow['agreementId'] = row[0]
        temprow['jobId'] = row[1]
        temprow['owner'] = row[2]
        temprow['status'] = row[3]
        temprow['statusText'] = row[4]
        temprow['dateCreated'] = row[5]
        temprow['namespace'] = row[6]
        result.append(temprow)
    return result


def create_sql_job(agreement_id, job_id, owner, body, namespace):
    postgres_insert_query = """
        INSERT 
            INTO jobs 
                (agreementId,workflowId,owner,status,statusText,workflow,namespace) 
            VALUES 
                (%s, %s, %s, %s, %s,%s,%s)"""
    record_to_insert = (str(agreement_id), str(job_id), str(owner), 1, "Warming up", json.dumps(body), namespace)
    return _execute_query(postgres_insert_query, record_to_insert, 'create_sql_job')


def stop_sql_job(execution_id):
    postgres_insert_query = """UPDATE jobs SET stopreq=1 WHERE workflowId=%s"""
    record_to_insert = (str(execution_id),)
    return _execute_query(postgres_insert_query, record_to_insert, 'stop_sql_job')


def remove_sql_job(execution_id):
    postgres_insert_query = """ UPDATE jobs SET removed=1 WHERE workflowId=%s"""
    record_to_insert = (str(execution_id),)
    return _execute_query(postgres_insert_query, record_to_insert, 'remove_sql_job')


def get_pg_connection_and_cursor():
    try:
        connection = psycopg2.connect(
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            database=os.getenv("POSTGRES_DB")
        )
        connection.set_client_encoding('LATIN9')
        cursor = connection.cursor()
        return connection, cursor
    except (Exception, psycopg2.Error) as error:
        logging.error(f'New PG connect error: {error}')
        return None, None


def _execute_query(query, record, msg, get_rows=False):
    connection, cursor = get_pg_connection_and_cursor()
    if not connection or not cursor:
        return

    try:
        cursor.execute(query, record)
        if get_rows:
            result = []
            row = cursor.fetchone()
            while row is not None:
                result.append(row)
                row = cursor.fetchone()
            return result
        else:
            connection.commit()

    except (Exception, psycopg2.Error) as error:
        logging.error(f'Got PG error in {msg}: {error}')
    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
