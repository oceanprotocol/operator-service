#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import json
from unittest.mock import Mock, MagicMock
import uuid

from eth_utils import add_0x_prefix
from ocean_keeper.utils import add_ethereum_prefix_and_hash_msg
from ocean_utils.agreements.service_agreement import ServiceAgreement
from ocean_utils.agreements.service_types import ServiceTypes
from ocean_utils.aquarius.aquarius import Aquarius
from ocean_utils.http_requests.requests_session import get_requests_session
from werkzeug.utils import get_content_type

from ocean_utils.did import DID, did_to_id

from operator_service.constants import BaseURLs

COMPUTE_ENDPOINT = BaseURLs.BASE_OPERATOR_URL + '/services/compute'


def dummy_callback(*_):
    pass


# def test_operator(client):
#     rv = client.get('/')
#     assert json.loads(rv.data.decode('utf-8'))['software'] == 'Operator service'


def _get_stage():
    return {
        'index': 0,
        'input': [
            {
                'index': 0,
                'id': 'did:op:1c8b66c24a6c774677741647adb0710f7a4afeea3e5b7f14fdb5f5e650c0eafd',
                'url': [
                    'https://raw.githubusercontent.com/tbertinmahieux/'
                    'MSongsDB/master/Tasks_Demos/CoverSongs/shs_dataset_test.txt'
                ]
            }
        ],
        'compute': {
            'Instances': 1,
            'namespace': 'ocean-compute',
            'maxtime': 3600
        },
        'algorithm': {
            'id': 'did:op:cfba42c7ff30fdb2051ffebda727449f26185273a7cf712fd0ac07785bb714ac',
            'url': 'https://raw.githubusercontent.com/oceanprotocol/test-algorithm/master/javascript/algo.js',
            'rawcode': '',
            'container': {
                'entrypoint': 'node $ALGO', 'image': 'node', 'tag': '10'
            }
        },
        'output': {
            'nodeUri': 'http://127.0.0.1:8545',
            'brizoUri': 'http://localhost:8030',
            'brizoAddress': '0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e',
            'metadata': {'name': 'Workflow output'},
            'metadataUri': None,
            'secretStoreUri': 'http://127.0.0.1:12001',
            'owner': '0x068Ed00cF0441e4829D9784fCBe7b9e26D4BD8d0',
            'publishOutput': 1,
            'publishAlgorithmLog': 1
        }
    }


def test_start_compute_job(client):
    endpoint = BaseURLs.BASE_OPERATOR_URL + '/compute'

    payload = {
        'workflow': {
            'stages': [
                _get_stage()
            ]
        },
        'signature': '0x8e55fc6534378b47b4a1754c8b33613cbc7d3bd45463f87fb5d55ec0df0b8ab343'
                     '5d238ccb0a0562595e55376806aca1b3dc3bd124363073663505a89c2a26b41c',
        'agreementId': '0x1f6d583558b449aca6039545bb6282b88601005c76ad44c2b136a29c59e572b3',
        'owner': '0x068Ed00cF0441e4829D9784fCBe7b9e26D4BD8d0'
    }

    response = client.post(
        endpoint,
        data=json.dumps(payload),
        content_type='application/json'
    )
    assert response.status_code in (200, 201), f'start compute job failed: {response.data}'


def test_stop_compute_job(client):
    return


def test_delete_compute_job(client):
    return


def test_get_compute_job_status(client):
    return
