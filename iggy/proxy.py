
from iggy.interface import ServiceInterface

class ServiceProxy(object):
    def __init__(self, config):
        self.config = config
        self.services = {}

    def __getattr__(self, name):
        try:
            return self.services[name]
        except KeyError:
            try:
                uri = self.config['services'][name]
            except KeyError:
                uri = self.config['default_uri']
            uri = uri.format(service=name)
            self.services[name] = ServiceInterface(name, uri)
            return self.services[name]
