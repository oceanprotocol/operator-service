#
# Copyright 2022 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import os

import requests

API_URL = "http://172.15.0.13:31000/api/v1/operator"
os.environ["ALLOWED_ADMINS"] = '["0x6d39a833d1a6789aeca50db85cb830bc08319f45"]'

# Test with no headers
pgsql_init_response = requests.post(f"{API_URL}/pgsqlinit")
assert pgsql_init_response.status_code == 400
assert "Admin header is empty." in pgsql_init_response.text


# Test with no allowed admin
headers = {"Admin": None}
pgsql_init_response = requests.post(f"{API_URL}/pgsqlinit", headers=headers)
assert pgsql_init_response.status_code == 400
assert "Admin header is empty." in pgsql_init_response.text

# Test with foo admin
headers = {"Admin": "foo_admin"}
pgsql_init_response = requests.post(f"{API_URL}/pgsqlinit", headers=headers)
assert pgsql_init_response.status_code == 401
assert (
    "Access admin route failed due to invalid admin address."
    in pgsql_init_response.text
)

# Test with the right admin
headers = {"Admin": "0x6d39a833d1a6789aeca50db85cb830bc08319f45"}
pgsql_init_response = requests.post(f"{API_URL}/pgsqlinit", headers=headers)
assert pgsql_init_response.status_code == 200
assert "" in pgsql_init_response.text

del os.environ["ALLOWED_ADMINS"]
