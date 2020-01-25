from configparser import ConfigParser


class Config:
    def __init__(self):
        config_parser = ConfigParser()
        self.configuration = config_parser.read('/operator-service/config.ini')
        self.group = config_parser.get('resources', 'group')  # str | The custom resource's group name
        self.version = config_parser.get('resources', 'version')  # str | The custom resource's version
        self.namespace = config_parser.get('resources', 'namespace')  # str | The custom resource's namespace
        self.plural = config_parser.get('resources', 'plural')  # str | The custom resource's plural name. For TPRs this would be
