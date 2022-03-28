#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import pytest

import operator_service.routes
from operator_service.run import app

FAKE_UUID = "fake-uuid"


@pytest.fixture
def client():
    app.testing = True
    client = app.test_client()
    yield client


@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch):
    from .kube_mock import KubeAPIMock
    from .sql_mock import SQLMock

    def mock_uuid():
        return FAKE_UUID

    monkeypatch.setattr(operator_service.routes, "generate_new_id", mock_uuid)
    monkeypatch.setattr(operator_service.routes, "KubeAPI", KubeAPIMock)
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
