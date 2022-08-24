#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import os

from flask import Flask
from flask_cors import CORS
from flask_sieve import Sieve

from operator_service.log import setup_logging

setup_logging()

app = Flask(__name__)
CORS(app)
Sieve(app)

if "CONFIG_FILE" in os.environ and os.environ["CONFIG_FILE"]:
    app.config["CONFIG_FILE"] = os.environ["CONFIG_FILE"]
else:
    app.config["CONFIG_FILE"] = "config.ini"


app.config["SIEVE_INVALID_STATUS_CODE"] = 400
