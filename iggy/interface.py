
import urllib2
from iggy import serializer

class ServiceException(Exception):
    def __init__(self, msg, traceback):
        self.msg = msg
        self.traceback = traceback

    def __str__(self):
        return "%s\n%s" % (self.msg, "\n%s" % self.traceback if self.traceback else "")

class ExceptionCreator(object):
    def __getattr__(self, name):
        cls = type(name, (ServiceException,), {})
        setattr(self, name, cls)
        return cls

class ServiceRequest(object):
    def __init__(self, method, params):
        self.method = method
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
        self._url = (url if url.endswith('/') else url+"/").format(name=name)
        self.exception = ExceptionCreator()

    def __getattr__(self, name):
        return MethodProxy(self, name)

    def __call__(self, method, *args, **kwargs):
        if len(args) > 0:
            raise TypeError("Proxied functions do not allow positional arguments")

        request = ServiceRequest(method, kwargs)
        response = self.perform(request)
        if response.error:
            error = response.error
            raise getattr(self.exception, error['type'])(error['message'], error.get('traceback'))
        return response.result

    def perform(self, request):
        sarg = serializer.dumps(request.params)
        response = urllib2.urlopen("%s%s/" % (self._url, request.method), sarg)
        res = serializer.loads(response.read())
        return ServiceResponse(res.get('result'), res.get('error'))
