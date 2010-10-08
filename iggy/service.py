
import sys, traceback
from iggy import serializer

class DispatchError(Exception):
    def __init__(self, msg):
        self.msg = msg

class WSGIService(object):
    def __init__(self, services=None):
        self.services = services or {}
        self.serializer = serializer

    def __call__(self, environ, start_response):
        # import pprint
        # pprint.pprint(environ)

        path = environ['PATH_INFO'].split('/')
        service = path[1]
        method = path[2]

        content_length = environ.get('CONTENT_LENGTH')
        if content_length:
            body = environ['wsgi.input'].read(int(content_length))
        else:
            body = environ['wsgi.input'].read()

        svc = self.services[service]
        middleware = getattr(svc, 'middleware', [])

        params = self.serializer.loads(body)
        try:
            method = self._find_method(svc, method)
            params = dict((str(k), v) for k, v in params.items())
            res = self._execute_method(method, params, middleware)
        except DispatchError, exc:
            res = {
                'error': {
                    'type': 'DispatchError',
                    'message': exc.msg,
                    'traceback': None,
                },
                'result': None,
            }

        try:
            response = self.serializer.dumps(res)
        except TypeError, exc:
            tb = '\n'.join(traceback.format_exception(*sys.exc_info()))
            response = self.serializer.dumps(dict(
                error = {
                    'type': "SerializeFail",
                    'message': "Can't serialize: %r (%s)" % (res, exc),
                    'traceback': tb,
                },
                result = None,
            ))        

        status = '200 OK'
        headers = [
            ('Content-type',   'text/json-zlib'),
            ('Content-Length', str(len(response))),
        ]
        start_response(status, headers)
        return [response]

    def _find_method(self, svc, method_name):
        if not method_name or method_name.startswith('_'):
            raise DispatchError("Invalid method name %r" % method_name)

        try:
            method = getattr(svc, method_name)
        except AttributeError:
            raise DispatchError("Unknown method %r" % method_name)

        return method
    
    def _execute_method(self, method, params, middleware=[]):
        for m in middleware:
            if hasattr(m, 'request'):
                m.request(method, params)

        try:
            res = method(**params)
        except Exception, exc:
            for m in middleware:
                if hasattr(m, 'exception'):
                    m.exception(method, params, exc)
            tb = '\n'.join(traceback.format_exception(*sys.exc_info()))
            res = dict(
                result = None,
                error = {
                    'type': exc.__class__.__name__,
                    'message': str(exc),
                    'traceback': tb,
                },
            )
        else:
            for m in middleware:
                if hasattr(m, 'response'):
                    m.response(method, params, res)
            res = dict(
                result = res,
                error = None,
            )

        return res
    
    def register_service(self, clas, name=None):
        obj = clas
        if not isinstance(clas, type):
            clas = clas.__class__
        name = name or getattr(obj, "name", None) or clas.__name__.lower() #"%s.%s" % (clas.__module__, clas.__name__)

        self.services[name] = obj
