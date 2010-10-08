
import unittest, time, datetime

from gearpc import GPCWorker, GPCInterface, GPCException

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

class WorkHooks(object):
    def start(self, job):
        pass

    def fail(self, job, exc):
        print exc

    def complete(self, job, result):
        pass

class TestRemote(unittest.TestCase):
    def setUp(self):
        # Bit of a hack to use a class attribute for the log, but until the worker gets killed at the end of the test we need to do this
        self.mid = TestMiddlware()
        for x in list(self.mid.log):
            self.mid.log.remove(x)
        test_service = TestService()
        test_service.middleware = [self.mid]
        self.worker = GPCWorker(job_servers)
        self.worker.register_service(test_service)
        self.worker.register_service(NamedService())
        import thread
        thread.start_new_thread(self.worker.work, tuple(), dict(hooks=WorkHooks())) # TODO: Shouldn't use threads.. but we do for now (also, the thread is never terminated)
        self.interface = GPCInterface("%s.%s" % (TestService.__module__, TestService.__name__), job_servers)
        self.interface2 = GPCInterface("echoservice", job_servers)

    def tearDown(self):
        del self.worker
        del self.interface

    def testSuccess(self):
        self.failUnlessEqual(self.interface.echo(txt="foo"), "foo")

    def testAttributeDict(self):
        ret = self.interface.echo(txt={"foo": {"bar": "FTW"}})
        self.failUnlessEqual(ret.foo.bar, "FTW")

    def testFail(self):
        self.failUnlessRaises(self.interface.exception.FailedError, self.interface.fail)

    def testParallelCall(self):
        res = self.interface.pcall({1: ("echo", dict(txt="foo")), 2: ("echo", dict(txt="bar"))})
        self.failUnlessEqual(res, {1: 'foo', 2: 'bar'})

    def testDelayedCall(self):
        res = self.interface.pcall({1: self.interface.delayed.echo(txt="foo")})
        self.failUnlessEqual(res, {1: 'foo'})

    def testSuccessAfterFail(self):
        self.failUnlessRaises(GPCException, self.interface.fail)
        self.failUnlessEqual(self.interface.echo(txt="foo"), "foo")

    def testNamed(self):
        self.failUnlessEqual(self.interface2.echo(txt="foo"), "foo")

    def testPositionalArguments(self):
        self.failUnlessRaises(TypeError, lambda:self.interface.echo("foo"))

    def testDateTime(self):
        now = datetime.datetime.now()
        self.failUnlessEqual(self.interface.echo(txt=now), now)
        date = now.date()
        self.failUnlessEqual(self.interface.echo(txt=date), date)
        time = now.time()
        self.failUnlessEqual(self.interface.echo(txt=time), time)

    def testMiddlware(self):
        self.failUnlessEqual(self.interface.echo(txt="foo"), "foo")
        self.failUnlessEqual([x[0] for x in self.mid.log], ["request", "response"])
        self.failUnlessRaises(GPCException, self.interface.fail)
        self.failUnlessEqual([x[0] for x in self.mid.log], ["request", "response", "request", "exception"])

    def testUnknownFunction(self):
        self.failUnlessRaises(GPCException, self.interface.unknown)

class TestLocal(unittest.TestCase):
    def setUp(self):
        self.interface = GPCInterface("%s.%s" % (TestService.__module__, TestService.__name__), None)

    def tearDown(self):
        del self.interface

    def testSuccess(self):
        self.failUnlessEqual(self.interface.echo(txt="foo"), "foo")

    def testFail(self):
        self.failUnlessRaises(self.interface.exception.FailedError, self.interface.fail)

    def testUnknownFunction(self):
        self.failUnlessRaises(AttributeError, self.interface.unknown)

if __name__ == '__main__':
    unittest.main()
