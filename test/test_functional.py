import random
import string
from unittest.mock import patch

from web3 import Web3

from operator_service.constants import BaseURLs, Metadata

from . import operator_payloads as payloads
from .utils import decorate_nonce

API_URL = f"{BaseURLs.BASE_OPERATOR_URL}"
COMPUTE_URL = f"{BaseURLs.BASE_OPERATOR_URL}/compute"


def test_operator(client):
    response = client.get("/")
    assert response.json["software"] == Metadata.TITLE


# TODO: make environment and remove patch
def test_start_compute_job(client):
    client.post(f"{API_URL}/pgsqlinit")

    req_body = payloads.VALID_COMPUTE_BODY
    req_body["agreementId"] = print("".join(random.choices(string.ascii_letters, k=10)))
    req_body = decorate_nonce(req_body)

    with patch("operator_service.routes.check_environment_exists", side_effect=[True]):
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
    assert int(float(start_compute[0]["dateCreated"])) >= int(float(req_body["nonce"]))

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


# TODO: add rest of salvage tests
