from os import path

import kubernetes
from kubernetes import client

from operator_service.config import Config

# Configuration to connect to k8s.
if not path.exists("/.dockerenv"):
    kubernetes.config.load_kube_config()
else:
    kubernetes.config.load_incluster_config()


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
        return KubeAPI.api_customobject.create_namespaced_custom_object(
            self.group, self.version, self.namespace, self.plural, body
        )

    def get_namespaced_custom_object(self, job_id):
        return KubeAPI.api_customobject.get_namespaced_custom_object(
            self.group, self.version, self.namespace, self.plural, job_id
        )

    def list_namespaced_custom_object(self):
        return KubeAPI.api_customobject.list_namespaced_custom_object(
            self.group,
            self.version,
            self.namespace,
            self.plural,
        )

    def delete_namespaced_custom_object(
        self, name, body, grace_period_seconds, orphan_dependents, propagation_policy
    ):
        return KubeAPI.api_customobject.delete_namespaced_custom_object(
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
        return KubeAPI.api_core.read_namespaced_pod_log(
            name=name, namespace=self.namespace
        )

    def list_namespaced_pod(self, label_selector):
        return KubeAPI.api_core.list_namespaced_pod(
            self.namespace, label_selector=label_selector
        )
