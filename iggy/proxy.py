
from iggy.interface import ServiceInterface

class ServiceProxy(object):
    def __init__(self, config):
        self.config = config
        self.services = {}

    def __getattr__(self, name):
        try:
            return self.services[name]
        except KeyError:
            self.services[name] = ServiceInterface(name, self.config['services'][name])
            return self.services[name]
