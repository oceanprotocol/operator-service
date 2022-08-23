import json
import random
import string
import time
from unittest.mock import patch

from web3 import Web3

from operator_service.constants import BaseURLs, Metadata
from operator_service.data_store import get_pg_connection_and_cursor

from . import operator_payloads as payloads
from .utils import decorate_nonce

API_URL = f"{BaseURLs.BASE_OPERATOR_URL}"
COMPUTE_URL = f"{BaseURLs.BASE_OPERATOR_URL}/compute"


def test_operator(client):
    response = client.get("/")
    assert response.json["software"] == Metadata.TITLE


def test_start_compute_job(client, monkeypatch):
    monkeypatch.setenv(
        "ALLOWED_ADMINS", '["0x6d39a833d1a6789aeca50db85cb830bc08319f45"]'
    )
    headers = {"Admin": "0x6d39a833d1a6789aeca50db85cb830bc08319f45"}

    client.post(f"{API_URL}/pgsqlinit", headers=headers)

    connection, cursor = get_pg_connection_and_cursor()
    cursor.execute("TRUNCATE jobs")
    cursor.execute("TRUNCATE envs")
    insert_query = """
        INSERT INTO envs(namespace, status) VALUES('ocean-compute', '{"allowedChainId":1}')
    """
    cursor.execute(insert_query)
    connection.commit()

    req_body = payloads.VALID_COMPUTE_BODY
    req_body["agreementId"] = "".join(random.choices(string.ascii_letters, k=10))
    req_body = decorate_nonce(req_body)

    start_compute_response = client.post(COMPUTE_URL, json=req_body)
    assert start_compute_response.status_code == 200
    start_compute = start_compute_response.json
    assert len(start_compute) == 1
    assert start_compute[0]["agreementId"]
    assert start_compute[0]["jobId"]
    assert start_compute[0]["owner"] == req_body["owner"]
    assert start_compute[0]["statusText"] == "Warming up"
    assert (
        start_compute[0]["algoDID"]
        == req_body["workflow"]["stages"][0]["algorithm"]["id"]
    )
    assert (
        start_compute[0]["inputDID"][0]
        == req_body["workflow"]["stages"][0]["input"][0]["id"]
    )
    assert int(float(start_compute[0]["dateCreated"]))

    # Get the compute job status
    req_body = decorate_nonce(
        {
            "agreementId": start_compute[0]["agreementId"],
            "owner": start_compute[0]["owner"],
            "jobId": start_compute[0]["jobId"],
        }
    )
    compute_status_response = client.get(COMPUTE_URL, json=req_body)
    assert compute_status_response.status_code == 200
    compute_status = compute_status_response.json
    assert len(compute_status) == 1
    assert compute_status[0]["agreementId"]
    assert compute_status[0]["jobId"]
    assert compute_status[0]["owner"] == req_body["owner"]
    assert compute_status[0]["statusText"] == "Warming up"
    assert compute_status[0]["algoDID"] == start_compute[0]["algoDID"]
    assert compute_status[0]["inputDID"][0] == start_compute[0]["inputDID"][0]
    assert int(float(compute_status[0]["dateCreated"])) == int(float(req_body["nonce"]))

    # Get running jobs
    get_environments_response = client.get(f"{API_URL}/runningjobs")
    assert get_environments_response.status_code == 200
    get_env_status = get_environments_response.json
    assert len(get_env_status) == 1
    assert get_env_status[0]["agreementId"]
    assert get_env_status[0]["jobId"]
    assert get_env_status[0]["owner"] == req_body["owner"]
    assert get_env_status[0]["statusText"] == "Warming up"
    assert get_env_status[0]["algoDID"] == start_compute[0]["algoDID"]
    assert get_env_status[0]["inputDID"][0] == start_compute[0]["inputDID"][0]
    assert int(float(get_env_status[0]["dateCreated"])) == int(float(req_body["nonce"]))

    # Stop compute job
    req_body = decorate_nonce(
        {
            "owner": start_compute[0]["owner"],
            "jobId": start_compute[0]["jobId"],
        }
    )
    stop_compute_response = client.put(f"{API_URL}/compute", json=req_body)
    assert stop_compute_response.status_code == 200
    stop_compute = stop_compute_response.json
    assert len(stop_compute) == 1
    assert stop_compute[0]["stopreq"] == 1

    time.sleep(5)
    # Delete compute job
    req_body = decorate_nonce(
        {
            "agreementId": start_compute[0]["agreementId"],
            "owner": start_compute[0]["owner"],
            "jobId": start_compute[0]["jobId"],
        }
    )
    delete_compute_response = client.delete(f"{API_URL}/compute", json=req_body)
    assert delete_compute_response.status_code == 200
