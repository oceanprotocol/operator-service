from datetime import datetime
from eth_keys import KeyAPI
from eth_keys.backends import NativeECCBackend
from unittest.mock import patch
from operator_service.constants import BaseURLs, Metadata
from web3 import Web3

from . import operator_payloads as payloads
from .conftest import FAKE_UUID
from .kube_mock import KubeAPIMock
from .sql_mock import SQLMock, MOCK_JOB_STATUS

COMPUTE_URL = f"{BaseURLs.BASE_OPERATOR_URL}/compute"
keys = KeyAPI(NativeECCBackend)


def sign_message(message, wallet):
    """
    Signs the message with the private key of the given Wallet
    :param message: str
    :param wallet: Wallet instance
    :return: signature
    """
    keys_pk = keys.PrivateKey(wallet.key)
    hexable = Web3.toBytes(text=message) if isinstance(message, str) else message

    message_hash = Web3.solidityKeccak(
        ["bytes"],
        [Web3.toHex(hexable)],
    )
    prefix = "\x19Ethereum Signed Message:\n32"
    signable_hash = Web3.solidityKeccak(
        ["bytes", "bytes"], [Web3.toBytes(text=prefix), Web3.toBytes(message_hash)]
    )
    signed = keys.ecdsa_sign(message_hash=signable_hash, private_key=keys_pk)

    v = str(Web3.toHex(Web3.toBytes(signed.v)))
    r = str(Web3.toHex(Web3.toBytes(signed.r).rjust(32, b"\0")))
    s = str(Web3.toHex(Web3.toBytes(signed.s).rjust(32, b"\0")))

    signature = "0x" + r[2:] + s[2:] + v[2:]

    return signature


def decorate_nonce(payload):
    nonce = str(datetime.utcnow().timestamp())
    try:
        did = payload["workflow"]["stages"][0]["input"][0]["id"]
    except (KeyError, IndexError):
        did = ""

    wallet = payloads.VALID_WALLET

    msg = f"{wallet.address}{did}{nonce}"
    signature = sign_message(msg, wallet)

    payload["chainId"] = "13"
    payload["environment"] = "test1"
    payload["nonce"] = nonce
    payload["providerSignature"] = signature

    return payload


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

    monkeypatch.setenv("ALLOWED_PROVIDERS", str([payloads.VALID_WALLET.address]))

    with patch("operator_service.routes.check_environment_exists", side_effect=[True]):
        response = client.post(
            COMPUTE_URL, json=decorate_nonce(payloads.VALID_COMPUTE_BODY)
        )
    assert response.status_code == 200
    assert response.json == MOCK_JOB_STATUS

    response = client.post(COMPUTE_URL, json={})
    assert response.status_code == 400
    assert response.json["error"] == "payload seems empty."

    response = client.post(
        COMPUTE_URL, json=decorate_nonce(payloads.NO_WORKFLOW_COMPUTE_BODY)
    )
    assert response.status_code == 400
    assert (
        response.json["error"]
        == "`workflow` is required in the payload and must include workflow stages"
    )

    with patch("operator_service.routes.check_environment_exists", side_effect=[True]):
        response = client.post(
            COMPUTE_URL, json=decorate_nonce(payloads.NO_STAGES_COMPUTE_BODY)
        )
    assert response.status_code == 400
    assert response.json["error"] == "Missing stages"

    with patch("operator_service.routes.check_environment_exists", side_effect=[True]):
        response = client.post(
            COMPUTE_URL, json=decorate_nonce(payloads.INVALID_STAGE_COMPUTE_BODY)
        )
    assert response.status_code == 400
    assert response.json["error"] == "Missing algorithm in stage 0"

    monkeypatch.setenv("ALGO_POD_TIMEOUT", str(1200))
    monkeypatch.setattr(KubeAPIMock, "expected_maxtime", 1200)

    with patch("operator_service.routes.check_environment_exists", side_effect=[True]):
        response = client.post(
            COMPUTE_URL, json=decorate_nonce(payloads.VALID_COMPUTE_BODY)
        )
    assert response.status_code == 200
    assert response.json == MOCK_JOB_STATUS

    with patch("operator_service.routes.check_environment_exists", side_effect=[True]):
        response = client.post(
            COMPUTE_URL,
            json=decorate_nonce(payloads.VALID_COMPUTE_BODY_WITH_NO_MAXTIME),
        )
    assert response.status_code == 200
    assert response.json == MOCK_JOB_STATUS


def test_stop_compute_job(client, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_agreement_id", "fake-agreement-id")
        m.setattr(SQLMock, "expected_owner", "fake-owner")
        response = client.put(
            COMPUTE_URL,
            json=decorate_nonce(
                {
                    "agreementId": SQLMock.expected_agreement_id,
                    "owner": SQLMock.expected_owner,
                }
            ),
        )
        assert response.status_code == 200
        assert response.json == MOCK_JOB_STATUS
        SQLMock.assert_all_jobs_stopped_and_reset()

    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_owner", "fake-owner")
        m.setattr(SQLMock, "expected_job_id", "fake-job-id")
        response = client.put(
            COMPUTE_URL,
            json=decorate_nonce(
                {"jobId": SQLMock.expected_job_id, "owner": SQLMock.expected_owner}
            ),
        )
        assert response.status_code == 200
        assert response.json == MOCK_JOB_STATUS
        SQLMock.assert_all_jobs_stopped_and_reset()

    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_owner", "fake-owner")
        response = client.put(
            COMPUTE_URL, json=decorate_nonce({"owner": SQLMock.expected_owner})
        )
        assert response.status_code == 200
        assert response.json == MOCK_JOB_STATUS
        SQLMock.assert_all_jobs_stopped_and_reset()

    response = client.put(COMPUTE_URL, json={})
    assert response.status_code == 400


def test_delete_compute_job(client, monkeypatch):
    response = client.delete(COMPUTE_URL, json={})
    assert response.status_code == 200
    assert response.json == ""


def test_get_compute_job_status(client, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_agreement_id", "fake-agreement-id", "fake-chain-id")
        with patch(
            "operator_service.routes.check_environment_exists", side_effect=[True]
        ):
            response = client.get(
                COMPUTE_URL,
                json=decorate_nonce({"agreementId": SQLMock.expected_agreement_id}),
            )
    assert response.status_code == 200
    assert response.json == MOCK_JOB_STATUS

    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_job_id", "fake-job-id")
        with patch(
            "operator_service.routes.check_environment_exists", side_effect=[True]
        ):
            response = client.get(
                COMPUTE_URL, json=decorate_nonce({"jobId": SQLMock.expected_job_id})
            )

    assert response.status_code == 200
    assert response.json == MOCK_JOB_STATUS

    with monkeypatch.context() as m:
        m.setattr(SQLMock, "expected_owner", "fake-owner")
        with patch(
            "operator_service.routes.check_environment_exists", side_effect=[True]
        ):
            response = client.get(
                COMPUTE_URL, json=decorate_nonce({"owner": SQLMock.expected_owner})
            )

    assert response.status_code == 200
    assert response.json == MOCK_JOB_STATUS

    response = client.get(COMPUTE_URL, json={})
    assert response.status_code == 400
