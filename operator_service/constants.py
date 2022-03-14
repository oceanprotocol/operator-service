#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0


class ConfigSections:
    RESOURCES = "resources"


class BaseURLs:
    BASE_OPERATOR_URL = "/api/v1/operator"
    SWAGGER_URL = "/api/v1/docs"  # URL for exposing Swagger UI (without trailing '/')


class Metadata:
    TITLE = "Operator service"
    DESCRIPTION = (
        "Infrastructure Operator Micro-service"
        ". When running with our Docker images, "
        "it is exposed under `http://localhost:8050`."
    )
    HOST = "operatorservice.com"
