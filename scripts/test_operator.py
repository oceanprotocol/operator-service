#
# Copyright 2022 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import requests

from conftest import consumer_wallet
from utils.operator_payloads import VALID_COMPUTE_BODY
from utils.signature import sign

api_url = "http://172.15.0.13:31000/api/v1/operator"

req_body = VALID_COMPUTE_BODY
wallet = consumer_wallet()
nonce, provider_signature = sign(owner=req_body["owner"], wallet=wallet)

req_body["providerSignature"] = provider_signature
req_body["nonce"] = nonce

# Start the compute job
start_compute_response = requests.post(f"{api_url}/compute", json=req_body)
assert start_compute_response.status_code == 200
assert (
    start_compute_response.text
    == '[{"agreementId": "0x0", "jobId": "7d15da96e74b4d0fa86c4c08eab660dc", "owner": '
    '"0xC41808BBef371AD5CFc76466dDF9dEe228d2BdAA", "status": 1, "statusText": "Warming up", "dateCreated": '
    '"1653574759.01596", "dateFinished": "null", "results": "", "stopreq": 0, "removed": 0, "algoDID": '
    '"did:op:87bdaabb33354d2eb014af5091c604fb4b0f67dc6cca4d18a96547bffdc27bcf", "inputDID": ['
    '"did:op:87bdaabb33354d2eb014af5091c604fb4b0f67dc6cca4d18a96547bffdc27bcf"]}] '
)

start_compute = start_compute_response.json()

# Get the compute job status
req_body = {
    "agreementId": start_compute["agreementId"],
    "owner": start_compute["owner"],
    "jobId": start_compute["jobId"],
}
compute_status_response = requests.get(f"{api_url}/compute", json=req_body)
assert compute_status_response.status_code == 200


# Get running jobs
# get_environments_response = requests.get(f"{api_url}/runningjobs")
# assert get_environments_response.status_code == 200
