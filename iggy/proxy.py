
from iggy.interface import ServiceInterface

class ServiceProxy(object):
    def __init__(self, services=None, default_uri=None, interface_class=None):
        self.services = services or {}
        self.default_uri = default_uri
        self.interface_class = interface_class or ServiceInterface

    def __getattr__(self, name):
        try:
            return self.services[name]
        except KeyError:
            try:
                uri = self.services[name]
            except KeyError:
                uri = self.default_uri
            uri = uri.format(service=name)
            self.services[name] = self.interface_class(name, uri)
            return self.services[name]
