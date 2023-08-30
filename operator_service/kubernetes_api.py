import base64
from tempfile import NamedTemporaryFile
import os
import logging
from os import path
import kubernetes
from kubernetes import client

from operator_service.config import Config


logger = logging.getLogger(__name__)
# Configuration to connect to k8s.
try:
    kubernetes.config.load_incluster_config()
except Exception as e:
    logger.error("Failed to load kubernetes config")
    exit(1)


class KubeAPI:
    # create instances of the API classes
    api_customobject = client.CustomObjectsApi()
    api_core = client.CoreV1Api()

    def __init__(self, config=None):
        if config is None:
            config = Config()
        self.group = config.group
        self.version = config.version
        self.namespace = config.namespace
        self.plural = config.plural

    def create_namespaced_custom_object(self, body):
        return self.api_customobject.create_namespaced_custom_object(
            self.group, self.version, self.namespace, self.plural, body
        )

    def get_namespaced_custom_object(self, job_id):
        return self.api_customobject.get_namespaced_custom_object(
            self.group, self.version, self.namespace, self.plural, job_id
        )

    def list_namespaced_custom_object(self):
        return self.api_customobject.list_namespaced_custom_object(
            self.group,
            self.version,
            self.namespace,
            self.plural,
        )

    def delete_namespaced_custom_object(
        self, name, body, grace_period_seconds, orphan_dependents, propagation_policy
    ):
        return self.api_customobject.delete_namespaced_custom_object(
            self.group,
            self.version,
            self.namespace,
            self.plural,
            name,
            body,
            grace_period_seconds=grace_period_seconds,
            orphan_dependents=orphan_dependents,
            propagation_policy=propagation_policy,
        )

    def read_namespaced_pod_log(self, name):
        return self.api_core.read_namespaced_pod_log(
            name=name, namespace=self.namespace
        )

    def list_namespaced_pod(self, label_selector):
        return self.api_core.list_namespaced_pod(
            self.namespace, label_selector=label_selector
        )
