
import unittest, time, datetime
from wsgiref.simple_server import make_server

from iggy import WSGIService, ServiceInterface, ServiceProxy, ServiceException

job_servers = ["127.0.0.1"]

class FailedError(Exception):
    pass

class TestMiddlware(object):
    log = []

    def request(self, func, args):
        self.log.append(("request", func, args, None))

    def exception(self, func, args, exc):
        self.log.append(("exception", func, args, exc))

    def response(self, func, args, result):
        self.log.append(("response", func, args, result))

class TestService(object):
    def echo(self, txt):
        return txt

    def fail(self):
        raise FailedError("FAIL")

class NamedService(object):
    name = "echoservice"

    def echo(self, txt):
        return txt

def worker(services, *args, **kwargs):
    worker = WSGIService(services)
    httpd = make_server('127.0.0.1', 8000, worker)
    httpd.serve_forever()

class TestRemote(unittest.TestCase):
    def setUp(self):
        # Bit of a hack to use a class attribute for the log, but until the worker gets killed at the end of the test we need to do this
        self.mid = TestMiddlware()
        for x in list(self.mid.log):
            self.mid.log.remove(x)
        test_service = TestService()
        test_service.middleware = [self.mid]

        import multiprocessing
        self.worker = multiprocessing.Process(target=worker, args=({"testservice": test_service, "echoservice": NamedService()},))
        self.worker.start()
        time.sleep(0.5)

        self.proxy = ServiceProxy(
            {"services": {
                "testservice": "http://localhost:8000/{name}/",
                "echoservice": "http://localhost:8000/{name}/",
            }}
        )

    def tearDown(self):
        self.worker.terminate()
        self.worker.join()

    def testSuccess(self):
        self.failUnlessEqual(self.proxy.echoservice.echo(txt="foo"), "foo")

    def testAttributeDict(self):
        ret = self.proxy.echoservice.echo(txt={"foo": {"bar": "FTW"}})
        self.failUnlessEqual(ret.foo.bar, "FTW")

    def testFail(self):
        self.failUnlessRaises(self.proxy.testservice.exception.FailedError, self.proxy.testservice.fail)

    def testSuccessAfterFail(self):
        self.failUnlessRaises(ServiceException, self.proxy.testservice.fail)
        self.failUnlessEqual(self.proxy.testservice.echo(txt="foo"), "foo")

    def testNamed(self):
        self.failUnlessEqual(self.proxy.echoservice.echo(txt="foo"), "foo")

    def testPositionalArguments(self):
        self.failUnlessRaises(TypeError, lambda:self.proxy.testservice.echo("foo"))

    def testDateTime(self):
        now = datetime.datetime.now()
        self.failUnlessEqual(self.proxy.testservice.echo(txt=now), now)
        date = now.date()
        self.failUnlessEqual(self.proxy.testservice.echo(txt=date), date)
        time = now.time()
        self.failUnlessEqual(self.proxy.testservice.echo(txt=time), time)

    # def testMiddlware(self):
    #     self.failUnlessEqual(self.proxy.testservice.echo(txt="foo"), "foo")
    #     self.failUnlessEqual([x[0] for x in self.mid.log], ["request", "response"])
    #     self.failUnlessRaises(ServiceException, self.proxy.testservice.fail)
    #     self.failUnlessEqual([x[0] for x in self.mid.log], ["request", "response", "request", "exception"])

    def testUnknownFunction(self):
        self.failUnlessRaises(ServiceException, self.proxy.echoservice.unknown)

if __name__ == '__main__':
    unittest.main()
