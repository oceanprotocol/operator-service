#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import pytest

FAKE_UUID = "fake-uuid"


@pytest.fixture
def client():
    from operator_service.run import app
    app.testing = True
    client = app.test_client()
    yield client


@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch):
    from .kube_mock import KubeAPIMock
    from .sql_mock import SQLMock

    def mock_uuid():
        return FAKE_UUID
    
    def mock_get_signer(signature,message):
        return "0x1234"

    monkeypatch.setattr("kubernetes.config.load_kube_config", mock_uuid)

    import os
    current_dir = os.path.dirname(os.path.realpath(__file__))
    monkeypatch.setenv("CONFIG_FILE", f"{current_dir}/../config.ini")

    import operator_service.routes
    import operator_service.utils
   
    monkeypatch.setattr(operator_service.utils, "generate_new_id", mock_uuid)
    monkeypatch.setattr("operator_service.utils.get_signer", mock_get_signer)
    monkeypatch.setattr("operator_service.kubernetes_api.KubeAPI", KubeAPIMock)

    monkeypatch.setattr(
    operator_service.routes, "create_sql_job", SQLMock.mock_create_sql_job
    )
    monkeypatch.setattr(
        operator_service.routes, "get_sql_jobs", SQLMock.mock_get_sql_jobs
    )
    monkeypatch.setattr(
        operator_service.routes, "stop_sql_job", SQLMock.mock_stop_sql_job
    )
    monkeypatch.setattr(
        operator_service.routes, "remove_sql_job", SQLMock.mock_remove_sql_job
    )
    monkeypatch.setattr(
        operator_service.routes, "get_sql_status", SQLMock.mock_get_sql_status
    )
    monkeypatch.setattr(
        operator_service.routes, "check_environment_exists", SQLMock.check_environment_exists
    )
    

