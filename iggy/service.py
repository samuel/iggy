
class DispatchError(Exception):
    def __init__(self, msg):
        self.msg = msg

class Service(GearmanWorker):
    def __init__(self, *args, **kwargs):
        super(GPCWorker, self).__init__(*args, **kwargs)
        self.services = {}
        self.serializer = serializer

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

    def _dispatch(self, job):
        svc = self.services[job.func]
        middleware = getattr(svc, 'middleware', [])

        arg = self.serializer.loads(job.arg)
        self.handle_meta(arg)
        try:
            method = self._find_method(svc, arg.get('method'))
            params = dict((str(k), v) for k, v in arg['params'].items())
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
            return self.serializer.dumps(res)
        except TypeError, exc:
            tb = '\n'.join(traceback.format_exception(*sys.exc_info()))
            return self.serializer.dumps(dict(
                error = {
                    'type': "SerializeFail",
                    'message': "Can't serialize: %r (%s)" % (res, exc),
                    'traceback': tb,
                },
                result = None,
            ))

    def handle_meta(self, meta):
        """Can be overriden to handle additional meta arguments from RPC call"""
        return

    def register_service(self, clas, name=None):
        obj = clas
        if not isinstance(clas, type):
            clas = clas.__class__
        name = name or getattr(obj, "name", None) or "%s.%s" % (clas.__module__, clas.__name__)

        self.services[name] = obj
        self.register_function(name, self._dispatch)
