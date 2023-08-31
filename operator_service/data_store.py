import os
import logging

import psycopg2
import simplejson as json

logging.basicConfig(format="%(asctime)s %(message)s")
logger = logging.getLogger("operator-service")
logger.setLevel(logging.DEBUG)


def get_sql_status(agreement_id, job_id, owner, chain_id):
    # enforce strings
    params = dict()
    select_query = """
    SELECT agreementId, workflowId, owner, status, statusText,
        extract(epoch from dateCreated) as dateCreated,
        extract(epoch from dateFinished) as dateFinished,
        configlogURL, publishlogURL, algologURL, outputsURL, ddo, stopreq, removed , workflow
    FROM jobs WHERE 1=1
    """

    if agreement_id is not None:
        select_query = select_query + " AND agreementId=%(agreementId)s"
        params["agreementId"] = str(agreement_id)

    if job_id is not None:
        select_query = select_query + " AND workflowId=%(jobId)s"
        params["jobId"] = str(job_id)

    if owner is not None:
        select_query = select_query + " AND owner=%(owner)s"
        params["owner"] = str(owner)

    result = []
    rows = _execute_query(select_query, params, "get_sql_status", get_rows=True)
    if not rows:
        return result

    for row in rows:
        temprow = dict()
        temprow["agreementId"] = row[0]
        temprow["jobId"] = row[1]
        temprow["owner"] = row[2]
        temprow["status"] = row[3]
        temprow["statusText"] = row[4]
        temprow["dateCreated"] = row[5]
        temprow["dateFinished"] = row[6]
        # temprow['configlogUrl']=row[7]
        # temprow['publishlogUrl']=row[8]
        # temprow['algorithmLogUrl'] = row[9]
        temprow["results"] = ""
        if row[10] and len(str(row[10])) > 2:
            # need to filter url from object
            outputs = json.loads(str(row[10]))
            for i, entry in enumerate(outputs):
                if outputs[i] and "url" in outputs[i]:
                    del outputs[i]["url"]
            temprow["results"] = outputs
        # temprow['resultsDid'] = ''
        # if row[11] and len(str(row[11])) > 2:
        #    ddo_json = json.loads(str(row[11]))
        #    temprow['resultsDid'] = ddo_json.get('id', '')
        temprow["stopreq"] = row[12]
        temprow["removed"] = row[13]
        workflow_dict = json.loads(row[14])
        if chain_id and "chainId" in workflow_dict:
            if chain_id != workflow_dict["chain_id"]:
                continue
        stage = workflow_dict["spec"]["metadata"]["stages"][0]
        if "id" in stage["algorithm"]:
            temprow["algoDID"] = stage["algorithm"]["id"]
        else:
            temprow["algoDID"] = "raw"
        temprow["inputDID"] = list()
        for input in stage["input"]:
            if "id" in input:
                temprow["inputDID"].append(input["id"])
        result.append(temprow)
    return result


def get_sql_job_urls(job_id):
    # get outputsURL & job owner as a tuple
    params = dict()
    select_query = """
    SELECT owner, outputsURL FROM jobs WHERE workflowId=%(jobId)s
    """
    if job_id is None:
        return None, None

    params["jobId"] = str(job_id)
    rows = _execute_query(select_query, params, "get_sql_job_urls", get_rows=True)
    if not rows or len(rows) < 1:
        return None, None
    try:
        result = json.loads(str(rows[0][1]))
        owner = rows[0][0]
        return result, owner
    except:
        return None, None


def get_sql_jobs(agreement_id, job_id, owner):
    params = dict()
    select_query = "SELECT workflowId FROM jobs WHERE 1=1"
    if agreement_id is not None:
        select_query = select_query + " AND agreementId=%(agreementId)s"
        params["agreementId"] = str(agreement_id)
    if job_id is not None:
        select_query = select_query + " AND workflowId=%(jobId)s"
        params["jobId"] = str(job_id)
    if owner is not None:
        select_query = select_query + " AND owner=%(owner)s"
        params["owner"] = str(owner)
    try:
        rows = _execute_query(select_query, params, "get_sql_jobs", get_rows=True)
        if not rows:
            return []
        return [row[0] for row in rows]
    except (Exception, psycopg2.Error) as error:
        logger.error(f"PG query error: {error}")
        return


def get_sql_running_jobs():
    # enforce strings
    params = dict()
    select_query = """
    SELECT agreementId, workflowId, owner, status, statusText,
        extract(epoch from dateCreated) as dateCreated,
        namespace,workflow FROM jobs WHERE dateFinished IS NULL
    """
    result = []
    rows = _execute_query(select_query, params, "get_sql_status", get_rows=True)
    if not rows:
        return result
    for row in rows:
        temprow = dict()
        temprow["agreementId"] = row[0]
        temprow["jobId"] = row[1]
        temprow["owner"] = row[2]
        temprow["status"] = row[3]
        temprow["statusText"] = row[4]
        temprow["dateCreated"] = row[5]
        temprow["namespace"] = row[6]
        workflow_dict = json.loads(row[7])
        stage = workflow_dict["spec"]["metadata"]["stages"][0]
        if "chainId" in workflow_dict:
            temprow["chainId"] = workflow_dict["chainId"]
        if "id" in stage["algorithm"]:
            temprow["algoDID"] = stage["algorithm"]["id"]
        else:
            temprow["algoDID"] = "raw"
        temprow["inputDID"] = list()
        for input in stage["input"]:
            if "id" in input:
                temprow["inputDID"].append(input["id"])
        result.append(temprow)
    return result


def get_nonce_for_certain_provider(provider_address: str):
    params = dict()
    select_query = """SELECT nonce FROM nonces WHERE provider = %(provider)s"""
    params["provider"] = provider_address

    try:
        rows = _execute_query(select_query, params, "get_nonce", get_rows=True)
        if not rows:
            logger.info("nonce is null")
            return []
        values = []
        for row in rows:
            if isinstance(row[0], str) and len(row[0]) == 19:
                values.append(int(row[0]))
            else:
                values.append(float(row[0]))

        logger.info(f"nonce found: {max(values)}")
        return max(values)
    except (Exception, psycopg2.Error) as error:
        logger.error(f"PG query error: {error}")
        return


def update_nonce_for_a_certain_provider(nonce: str, provider_address: str):
    # check if provider address exists
    params = dict()
    select_query = """SELECT provider FROM nonces WHERE provider = %(provider)s"""
    params["provider"] = provider_address

    try:
        rows = _execute_query(select_query, params, "get_provider", get_rows=True)
        if not rows:
            # creates a new row if necessary
            postgres_insert_query = (
                """INSERT INTO nonces (provider, nonce) VALUES (%s, %s)"""
            )
            record_to_insert = (
                provider_address,
                nonce,
            )

            try:
                _execute_query(postgres_insert_query, record_to_insert, "create_nonce")
                logger.debug(f"create_nonce: {provider_address}, new nonce {nonce}")
                return
            except (Exception, psycopg2.Error) as error:
                logger.error(f"PG query error from creating nonce row: {error}")
                return
    except (Exception, psycopg2.Error) as error:
        logger.error(f"PG query error from getting the provider address: {error}")
        return

    postgres_insert_query = """UPDATE nonces SET nonce=%s WHERE provider=%s"""
    record_to_insert = (
        nonce,
        provider_address,
    )

    return _execute_query(postgres_insert_query, record_to_insert, "update_nonce")


def get_sql_environments(logger, chain_id):
    params = dict()
    select_query = """
    SELECT namespace, status,extract(epoch from lastping) as lastping from envs
    """
    result = []
    rows = _execute_query(select_query, params, "get_sql_environments", get_rows=True)
    if not rows:
        return result
    for row in rows:
        temprow = json.loads(row[1])
        if "allowedChainId" in temprow:
            if isinstance(temprow["allowedChainId"], list):
                if len(temprow["allowedChainId"]):
                    if not (chain_id in temprow["allowedChainId"]):
                        continue
        temprow["lastSeen"] = str(row[2])
        temprow["id"] = row[0]
        result.append(temprow)
    return result


def check_environment_exists(environment, chain_id):
    params = dict()
    select_query = """
    SELECT namespace, status,extract(epoch from lastping) as lastping from envs WHERE namespace=%(env)s
    """
    params["env"] = environment
    rows = _execute_query(
        select_query, params, "check_environment_exists", get_rows=True
    )
    if not rows:
        return False

    status = json.loads(rows[0][1])
    if "allowedChainId" in status:
        if isinstance(status["allowedChainId"], list):
            if len(status["allowedChainId"]):
                if not (chain_id in status["allowedChainId"]):
                    return False
    return True


def get_job_by_provider_and_owner(owner, provider):
    params = dict()
    select_query = """
        SELECT agreementId, workflowId, owner, status, statusText, 
        extract(epoch from dateCreated) as dateCreated, 
        namespace FROM jobs WHERE provider=%(provider)s
        AND owner=%(owner)s
        """
    params["owner"] = owner
    params["provider"] = provider
    result = []
    rows = _execute_query(
        select_query, params, "get_job_by_provider_and_owner", get_rows=True
    )
    if not rows:
        return result
    for row in rows:
        temprow = dict()
        temprow["agreementId"] = row[0]
        temprow["jobId"] = row[1]
        temprow["owner"] = row[2]
        temprow["status"] = row[3]
        temprow["statusText"] = row[4]
        temprow["dateCreated"] = row[5]
        temprow["namespace"] = row[6]
        result.append(temprow)
    return result


def create_sql_job(agreement_id, job_id, owner, body, namespace, provider_address):
    postgres_insert_query = """
        INSERT
            INTO jobs
                (agreementId,workflowId,owner,status,statusText,workflow,namespace,provider)
            VALUES
                (%s, %s, %s, %s, %s,%s,%s,%s)"""
    record_to_insert = (
        str(agreement_id),
        str(job_id),
        str(owner),
        1,
        "Warming up",
        json.dumps(body),
        namespace,
        provider_address,
    )
    return _execute_query(postgres_insert_query, record_to_insert, "create_sql_job")


def stop_sql_job(execution_id):
    postgres_insert_query = """UPDATE jobs SET stopreq=1 WHERE workflowId=%s"""
    record_to_insert = (str(execution_id),)
    return _execute_query(postgres_insert_query, record_to_insert, "stop_sql_job")


def remove_sql_job(execution_id):
    postgres_insert_query = """ UPDATE jobs SET removed=1 WHERE workflowId=%s"""
    record_to_insert = (str(execution_id),)
    return _execute_query(postgres_insert_query, record_to_insert, "remove_sql_job")


def get_pg_connection_and_cursor():
    try:
        connection = psycopg2.connect(
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT", 5432),
            database=os.getenv("POSTGRES_DB"),
        )
        connection.set_client_encoding("LATIN9")
        cursor = connection.cursor()
        return connection, cursor
    except (Exception, psycopg2.Error) as error:
        logger.error(f"New PG connect error: {error}")
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
        logger.error(f"Got PG error in {msg}: {error}")
    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
