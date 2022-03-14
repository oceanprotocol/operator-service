import os
from configparser import ConfigParser


class Config:
    def __init__(self):
        config_parser = ConfigParser()
        config_path = os.environ.get("CONFIG_FILE", "/operator-service/config.ini")
        if not os.path.exists(config_path):
            raise AssertionError(f"config file does not exist in {config_path}")

        self.configuration = config_parser.read(config_path)
        self.group = config_parser.get(
            "resources", "group"
        )  # str | The custom resource's group name
        self.version = config_parser.get(
            "resources", "version"
        )  # str | The custom resource's version
        self.namespace = config_parser.get(
            "resources", "namespace"
        )  # str | The custom resource's namespace
        self.plural = config_parser.get(
            "resources", "plural"
        )  # str | The custom resource's plural name. For TPRs this would be
