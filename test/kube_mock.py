from copy import deepcopy

import kubernetes

from operator_service.config import Config
from operator_service.utils import create_compute_job, get_compute_resources
from .conftest import FAKE_UUID
from .operator_payloads import VALID_COMPUTE_BODY
from .sql_mock import MOCK_JOBS_LIST


class KubeAPIMock:
    expected_maxtime = None
    removed_objects = []

    @staticmethod
    def assert_all_objects_removed_and_reset():
        for job in MOCK_JOBS_LIST:
            assert job in KubeAPIMock.removed_objects
        KubeAPIMock.removed_objects = []

    def __init__(self, _):
        pass

    def create_namespaced_custom_object(self, body):
        processed_workflow = deepcopy(VALID_COMPUTE_BODY["workflow"])
        stage_compute = processed_workflow["stages"][0]["compute"]
        stage_compute["resources"] = get_compute_resources()
        if KubeAPIMock.expected_maxtime:
            stage_compute["maxtime"] = KubeAPIMock.expected_maxtime
        config = Config()
        correct_body = create_compute_job(
            processed_workflow,
            FAKE_UUID,
            config.group,
            config.version,
            config.namespace,
        )
        assert body == correct_body

    def delete_namespaced_custom_object(self, name, body, **_):
        assert isinstance(body, kubernetes.client.V1DeleteOptions)
        KubeAPIMock.removed_objects.append(name)
