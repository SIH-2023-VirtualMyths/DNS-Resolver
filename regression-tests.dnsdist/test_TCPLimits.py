#!/usr/bin/env python
import struct
import time
import dns
from dnsdisttests import DNSDistTest, pickAvailablePort

try:
  range = xrange
except NameError:
  pass

class TestTCPLimits(DNSDistTest):

    # this test suite uses a different responder port
    # because it uses a different health check configuration
    _testServerPort = pickAvailablePort()
    _answerUnexpected = True

    _tcpIdleTimeout = 2
    _maxTCPQueriesPerConn = 5
    _maxTCPConnsPerClient = 3
    _maxTCPConnDuration = 5
    _config_template = """
    newServer{address="127.0.0.1:%s"}
    setTCPRecvTimeout(%s)
    setMaxTCPQueriesPerConnection(%s)
    setMaxTCPConnectionsPerClient(%s)
    setMaxTCPConnectionDuration(%s)
    """
    _config_params = ['_testServerPort', '_tcpIdleTimeout', '_maxTCPQueriesPerConn', '_maxTCPConnsPerClient', '_maxTCPConnDuration']
    _verboseMode = True

    def testTCPQueriesPerConn(self):
        """
        TCP Limits: Maximum number of queries
        """
        name = 'maxqueriesperconn.tcp.tests.powerdns.com.'
        query = dns.message.make_query(name, 'A', 'IN')
        conn = self.openTCPConnection()

        count = 0
        for idx in range(self._maxTCPQueriesPerConn):
            try:
                self.sendTCPQueryOverConnection(conn, query)
                response = self.recvTCPResponseOverConnection(conn)
                self.assertTrue(response)
                count = count + 1
            except:
                pass

        # this one should fail
        failed = False
        try:
            self.sendTCPQueryOverConnection(conn, query)
            response = self.recvTCPResponseOverConnection(conn)
            self.assertFalse(response)
            if not response:
                failed = True
            else:
                count = count + 1
        except:
            failed = True

        conn.close()
        self.assertTrue(failed)
        self.assertEqual(count, self._maxTCPQueriesPerConn)

    def testTCPConnsPerClient(self):
        """
        TCP Limits: Maximum number of conns per client
        """
        name = 'maxconnsperclient.tcp.tests.powerdns.com.'
        query = dns.message.make_query(name, 'A', 'IN')
        conns = []

        for idx in range(self._maxTCPConnsPerClient + 1):
            conns.append(self.openTCPConnection())

        count = 0
        failed = 0
        for conn in conns:
            try:
                self.sendTCPQueryOverConnection(conn, query)
                response = self.recvTCPResponseOverConnection(conn)
                if response:
                    count = count + 1
                else:
                    failed = failed + 1
            except:
                failed = failed + 1

        for conn in conns:
            conn.close()

        # wait a bit to be sure that dnsdist closed the connections
        # and decremented the counters on its side, otherwise subsequent
        # connections will be dropped
        time.sleep(1)

        self.assertEqual(count, self._maxTCPConnsPerClient)
        self.assertEqual(failed, 1)

    def testTCPDuration(self):
        """
        TCP Limits: Maximum duration
        """
        name = 'duration.tcp.tests.powerdns.com.'

        start = time.time()
        conn = self.openTCPConnection()
        # immediately send the maximum size
        conn.send(struct.pack("!H", 65535))

        count = 0
        while count < (self._maxTCPConnDuration * 20):
            try:
                # sleeping for only one second keeps us below the
                # idle timeout (setTCPRecvTimeout())
                time.sleep(0.1)
                conn.send(b'A')
                count = count + 1
            except Exception as e:
                print("Exception: %s!" % (e))
                break

        end = time.time()

        self.assertAlmostEqual(count / 10, self._maxTCPConnDuration, delta=2)
        self.assertAlmostEqual(end - start, self._maxTCPConnDuration, delta=2)

        conn.close()

class TestTCPFrontendLimits(DNSDistTest):

    # this test suite uses a different responder port
    # because it uses a different health check configuration
    _testServerPort = pickAvailablePort()
    _answerUnexpected = True

    _skipListeningOnCL = True
    _tcpIdleTimeout = 2
    _maxTCPConnsPerFrontend = 10
    _config_template = """
    newServer{address="127.0.0.1:%s"}
    setLocal("%s:%d", {maxConcurrentTCPConnections=%d})
    """
    _config_params = ['_testServerPort', '_dnsDistListeningAddr', '_dnsDistPort', '_maxTCPConnsPerFrontend']
    _verboseMode = True

    def testTCPConnsPerFrontend(self):
        """
        TCP Frontend Limits: Maximum number of conns per frontend
        """
        name = 'maxconnsperfrontend.tcp.tests.powerdns.com.'
        query = dns.message.make_query(name, 'A', 'IN')
        conns = []

        for idx in range(self._maxTCPConnsPerFrontend + 1):
            conns.append(self.openTCPConnection())

        count = 0
        failed = 0
        for conn in conns:
            try:
                self.sendTCPQueryOverConnection(conn, query)
                response = self.recvTCPResponseOverConnection(conn)
                if response:
                    count = count + 1
                else:
                    failed = failed + 1
            except:
                failed = failed + 1

        for conn in conns:
            conn.close()

        # wait a bit to be sure that dnsdist closed the connections
        # and decremented the counters on its side, otherwise subsequent
        # connections will be dropped
        time.sleep(1)

        self.assertEqual(count, self._maxTCPConnsPerFrontend)
        self.assertEqual(failed, 1)
