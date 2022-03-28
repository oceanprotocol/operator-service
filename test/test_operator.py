from operator_service.constants import BaseURLs, Metadata
from . import operator_payloads as payloads
from .conftest import FAKE_UUID
from .kube_mock import KubeAPIMock
from .sql_mock import SQLMock, MOCK_JOB_STATUS

COMPUTE_URL = f"{BaseURLs.BASE_OPERATOR_URL}/compute"


def test_operator(client):
    response = client.get("/")
    assert response.json["software"] == Metadata.TITLE


def test_start_compute_job(client, monkeypatch):
    monkeypatch.setattr(
        SQLMock, "expected_agreement_id", payloads.VALID_COMPUTE_BODY["agreementId"]
    )
    monkeypatch.setattr(SQLMock, "expected_job_id", FAKE_UUID)
    monkeypatch.setattr(SQLMock, "expected_owner", payloads.VALID_COMPUTE_BODY["owner"])

    monkeypatch.setattr(
        KubeAPIMock,
        "expected_maxtime",
        payloads.VALID_COMPUTE_BODY["workflow"]["stages"][0]["compute"]["maxtime"],
    )

    response = client.post(COMPUTE_URL, json=payloads.VALID_COMPUTE_BODY)
    assert response.status_code == 200
    assert response.json == MOCK_JOB_STATUS

    response = client.post(COMPUTE_URL, json={})
    assert response.status_code == 400

    response = client.post(COMPUTE_URL, json=payloads.NO_WORKFLOW_COMPUTE_BODY)
    assert response.status_code == 400

    response = client.post(COMPUTE_URL, json=payloads.NO_STAGES_COMPUTE_BODY)
    assert response.status_code == 400

    response = client.post(COMPUTE_URL, json=payloads.INVALID_STAGE_COMPUTE_BODY)
    assert response.status_code == 400

    monkeypatch.setenv("ALGO_POD_TIMEOUT", str(1200))
    monkeypatch.setattr(KubeAPIMock, "expected_maxtime", 1200)

    response = client.post(COMPUTE_URL, json=payloads.VALID_COMPUTE_BODY)
    assert response.status_code == 200
    assert response.json == MOCK_JOB_STATUS

    response = client.post(
        COMPUTE_URL, json=payloads.VALID_COMPUTE_BODY_WITH_NO_MAXTIME
    )
    assert response.status_code == 200
    assert response.json == MOCK_JOB_STATUS


def test_stop_compute_job(client, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_agreement_id", "fake-agreement-id")
        response = client.put(
            COMPUTE_URL, json={"agreementId": SQLMock.expected_agreement_id}
        )
        assert response.status_code == 200
        assert response.json == MOCK_JOB_STATUS
        SQLMock.assert_all_jobs_stopped_and_reset()

    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_job_id", "fake-job-id")
        response = client.put(COMPUTE_URL, json={"jobId": SQLMock.expected_job_id})
        assert response.status_code == 200
        assert response.json == MOCK_JOB_STATUS
        SQLMock.assert_all_jobs_stopped_and_reset()

    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_owner", "fake-owner")
        response = client.put(COMPUTE_URL, json={"owner": SQLMock.expected_owner})
        assert response.status_code == 200
        assert response.json == MOCK_JOB_STATUS
        SQLMock.assert_all_jobs_stopped_and_reset()

    response = client.put(COMPUTE_URL, json={})
    assert response.status_code == 400


def test_delete_compute_job(client, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_agreement_id", "fake-agreement-id")
        response = client.delete(
            COMPUTE_URL, json={"agreementId": SQLMock.expected_agreement_id}
        )
        assert response.status_code == 200
        assert response.json == MOCK_JOB_STATUS
        SQLMock.assert_all_jobs_removed_and_reset()
        KubeAPIMock.assert_all_objects_removed_and_reset()

    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_job_id", "fake-job-id")
        response = client.delete(COMPUTE_URL, json={"jobId": SQLMock.expected_job_id})
        assert response.status_code == 200
        assert response.json == MOCK_JOB_STATUS
        SQLMock.assert_all_jobs_removed_and_reset()
        KubeAPIMock.assert_all_objects_removed_and_reset()

    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_owner", "fake-owner")
        response = client.delete(COMPUTE_URL, json={"owner": SQLMock.expected_owner})
        assert response.status_code == 200
        assert response.json == MOCK_JOB_STATUS
        SQLMock.assert_all_jobs_removed_and_reset()
        KubeAPIMock.assert_all_objects_removed_and_reset()

    response = client.delete(COMPUTE_URL, json={})
    assert response.status_code == 400


def test_get_compute_job_status(client, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_agreement_id", "fake-agreement-id")
        response = client.get(
            COMPUTE_URL, json={"agreementId": SQLMock.expected_agreement_id}
        )
        assert response.status_code == 200
        assert response.json == MOCK_JOB_STATUS

    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_job_id", "fake-job-id")
        response = client.get(COMPUTE_URL, json={"jobId": SQLMock.expected_job_id})
        assert response.status_code == 200
        assert response.json == MOCK_JOB_STATUS

    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_owner", "fake-owner")
        response = client.get(COMPUTE_URL, json={"owner": SQLMock.expected_owner})
        assert response.status_code == 200
        assert response.json == MOCK_JOB_STATUS

    response = client.get(COMPUTE_URL, json={})
    assert response.status_code == 400
