
import urllib2
from iggy import serializer

class ServiceException(Exception):
    def __init__(self, msg, traceback):
        self.msg = msg
        self.traceback = traceback

    def __str__(self):
        return "%s\n%s" % (self.msg, "\n%s" % self.traceback if self.traceback else "")

class DispatchError(Exception):
    def __init__(self, msg):
        self.msg = msg

class ExceptionCreator(object):
    def __getattr__(self, name):
        cls = type(name, (ServiceException,), {})
        setattr(self, name, cls)
        return cls

class ServiceRequest(object):
    def __init__(self, method, params):
        self.methods = method
        self.params = params

class ServiceResponse(object):
    def __init__(self, result, error):
        self.result = result
        self.error = error

class MethodProxy(object):
    def __init__(self, interface, name):
        self.interface = interface
        self.name = name

    def __call__(self, *args, **kwargs):
        if len(args) > 0:
            raise TypeError("Proxied functions do not allow positional arguments")

        return self.interface(self.name, **kwargs)

class ServiceInterface(object):
    def __init__(self, name, url):
        self._name = name
        self._url = url if url.endswith('/') else url+"/"
        self.exception = ExceptionCreator()

    def __getattr__(self, name):
        return MethodProxy(self, name)

    def __call__(self, method, *args, **kwargs):
        if len(args) > 0:
            raise TypeError("Proxied functions do not allow positional arguments")

        sarg = serializer.dumps(kwargs)
        response = urllib2.urlopen("%s%s/" % (self._url, method), sarg)
        res = serializer.loads(response.read())

        if res['error']:
            raise getattr(self.exception, res['error']['type'])(res['error']['message'], res['error'].get('traceback'))
        return res['result']
