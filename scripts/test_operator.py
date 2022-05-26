#
# Copyright 2022 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import time

import requests

from conftest import consumer_wallet
from utils.operator_payloads import VALID_COMPUTE_BODY
from utils.signature import sign

API_URL = "http://172.15.0.13:31000/api/v1/operator"

req_body = VALID_COMPUTE_BODY
wallet = consumer_wallet()
nonce, provider_signature = sign(owner=req_body["owner"], wallet=wallet)

req_body["providerSignature"] = provider_signature
req_body["nonce"] = nonce

# Start the compute job
start_compute_response = requests.post(f"{API_URL}/compute", json=req_body)
assert start_compute_response.status_code == 200
start_compute = start_compute_response.json()
assert len(start_compute) == 1
assert start_compute[0]["agreementId"]
assert start_compute[0]["jobId"]
assert start_compute[0]["owner"] == req_body["owner"]
assert start_compute[0]["statusText"] == "Warming up"
assert (
    start_compute[0]["algoDID"] == req_body["workflow"]["stages"][0]["algorithm"]["id"]
)
assert (
    start_compute[0]["inputDID"][0]
    == req_body["workflow"]["stages"][0]["input"][0]["id"]
)
assert int(float(start_compute[0]["dateCreated"])) == int(nonce)

# Get the compute job status
req_body = {
    "agreementId": start_compute[0]["agreementId"],
    "owner": start_compute[0]["owner"],
    "jobId": start_compute[0]["jobId"],
    "providerSignature": provider_signature,
}
compute_status_response = requests.get(f"{API_URL}/compute", json=req_body)
assert compute_status_response.status_code == 200
compute_status = compute_status_response.json()
assert len(compute_status) == 1
assert compute_status[0]["agreementId"]
assert compute_status[0]["jobId"]
assert compute_status[0]["owner"] == req_body["owner"]
assert compute_status[0]["statusText"] == "Warming up"
assert compute_status[0]["algoDID"] == start_compute[0]["algoDID"]
assert compute_status[0]["inputDID"][0] == start_compute[0]["inputDID"][0]
assert int(float(compute_status[0]["dateCreated"])) == int(nonce)

# Get running jobs
get_environments_response = requests.get(f"{API_URL}/runningjobs")
assert get_environments_response.status_code == 200
compute_status = get_environments_response.json()
assert len(compute_status) == 1
assert compute_status[0]["agreementId"]
assert compute_status[0]["jobId"]
assert compute_status[0]["owner"] == req_body["owner"]
assert compute_status[0]["statusText"] == "Warming up"
assert compute_status[0]["algoDID"] == start_compute[0]["algoDID"]
assert compute_status[0]["inputDID"][0] == start_compute[0]["inputDID"][0]
assert int(float(compute_status[0]["dateCreated"])) == int(nonce)

# Stop compute job
req_body = {
    "owner": start_compute[0]["owner"],
    "jobId": start_compute[0]["jobId"],
    "providerSignature": provider_signature,
    "nonce": nonce,
}
stop_compute_response = requests.put(f"{API_URL}/compute", json=req_body)
assert stop_compute_response.status_code == 200
stop_compute = stop_compute_response.json()
assert len(stop_compute) == 1
assert stop_compute[0]["stopreq"] == 1

time.sleep(5)
# Delete compute job
req_body = {
    "agreementId": start_compute[0]["agreementId"],
    "owner": start_compute[0]["owner"],
    "jobId": start_compute[0]["jobId"],
    "providerSignature": provider_signature,
}
delete_compute_response = requests.delete(f"{API_URL}/compute", json=req_body)
assert delete_compute_response.status_code == 200
