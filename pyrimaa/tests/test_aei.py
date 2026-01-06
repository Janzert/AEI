# Copyright (c) 2015 Brian Haskin Jr.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE

import os.path
import socket
import sys
import unittest

from pyrimaa import aei, board
from pyrimaa.aei import EngineController, EngineException, EngineResponse


class MockEngine:
    def __init__(self, expected):
        self.log = None
        self.expected = expected
        self.event = 0
        self._closed = False

    def is_running(self):
        return False if self._closed else True

    def send(self, msg):
        if self._closed:
            raise Exception("Mock engine send called after cleanup.")
        expected = self.expected[self.event]
        if expected[0] == "raise":
            self.event += 1
            raise expected[1]
        if expected[0] != "s":
            raise Exception("Mock engine send called when expecting, %s" %
                            (expected, ))
        if msg.rstrip() != expected[1]:
            raise Exception(
                "Mock engine send called with unexpected message (%s) expected (%s)."
                % (msg, expected[1]))
        self.event += 1

    def readline(self, timeout=None):
        if self._closed:
            raise Exception("Mock engine readline called after cleanup.")
        expected = self.expected[self.event]
        if expected[0] != "r":
            raise Exception("Mock engine readline called when expecting, %s" %
                            (expected[1], ))
        self.event += 1
        return expected[1]

    def waitfor(self, msg, timeout=0.5):
        if self._closed:
            raise Exception("Mock engine waitfor called after cleanup.")
        msg = msg.rstrip()
        expected = self.expected[self.event]
        if expected[0] not in ["r", "raise"]:
            raise Exception("Mock engine waitfor called when expecting, %s" %
                            (expected, ))
        responses = []
        while expected[0] == "r" and expected[1] != msg:
            responses.append(expected[1])
            self.event += 1
            expected = self.expected[self.event]
        if expected[0] == "r" and msg == expected[1]:
            responses.append(expected[1])
        elif expected[0] == "send_response":
            pass
        elif expected[0] == "raise":
            self.event += 1
            raise expected[1]()
        else:
            raise Exception(
                "Mock engine waitfor called with unexpected message (%s)" %
                (msg, ))
        self.event += 1
        return responses

    def cleanup(self):
        if self._closed:
            raise Exception("Mock engine cleanup called multiple times.")
        self._closed = True


class MockLog:
    def __init__(self):
        self.debugging = ""
        self.information = ""
        self.warning = ""

    def debug(self, message):
        self.debugging += message + '\n'

    def info(self, message):
        self.information += message + '\n'

    def warn(self, message):
        self.warning += message + '\n'


protocol0 = [
    ("s", "aei"),
    ("r", "id name Mock0"),
    ("r", "id author Janzert"),
    ("r", "aeiok"),
    ("s", "isready"),
    ("r", "readyok"),
    ("s", "newgame"),
    ("s",
     "setposition w [rrrrrrrrdhcemchd                                DHCMECHDRRRRRRRR]"
    ),
]

bad_protocol = [
    ("s", "aei"),
    ("r", "protocol-version abc"),
    ("r", "id name Mock"),
    ("r", "id author Janzert"),
    ("r", "aeiok"),
    ("s", "isready"),
    ("r", "readyok"),
    ("s", "newgame"),
    ("s",
     "setposition g [rrrrrrrrdhcemchd                                DHCMECHDRRRRRRRR]"
    ),
    ("s", "go"),
    ("s", "stop"),
    ("s", "quit"),
]

protocol1 = [
    ("s", "aei"),
    ("r", "protocol-version 1"),
    ("r", "id name Mock"),
    ("r", "id author Janzert"),
    ("r", "aeiok"),
    ("s", "isready"),
    ("r", "log Engine running"),
    ("r", "readyok"),
    ("r", ""),
    ("r", "log Engine initialized"),
    ("s", "setoption name depth value 4"),
    ("s", "newgame"),
    ("s",
     "setposition g [rrrrrrrrdhcemchd                                DHCMECHDRRRRRRRR]"
    ),
    ("s", "go"),
    ("s", "stop"),
    ("r", "info depth 4"),
    ("r", "bestmove Hb2n Ed2n"),
    ("s", "makemove Hb2n Ed2n"),
    ("s", "go ponder"),
    ("s", "quit"),
]

bad_isready_response = [
    ("s", "aei"),
    ("r", "protocol-version 1"),
    ("r", "id name Mock"),
    ("r", "id author Janzert"),
    ("r", "aeiok"),
    ("s", "isready"),
    ("r", "readyok"),
    ("s", "newgame"),
    ("s", "isready"),
    ("r", "log Engine shutting down"),
    ("send_response",),
]

aeiok_timeout = [
    ("s", "aei"),
    ("raise", socket.timeout),
]

aei_send_error = [
    ("raise", IOError),
]

class EngineControllerTest(unittest.TestCase):
    def test_protocol_versions(self):
        eng = MockEngine(protocol0)
        ctl = EngineController(eng)
        self.assertEqual(ctl.ident["name"], "Mock0")
        self.assertEqual(ctl.ident["author"], "Janzert")
        self.assertEqual(ctl.protocol_version, 0)
        ctl.newgame()
        pos = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        ctl.setposition(pos)
        ctl.cleanup()
        # bad protocol version
        eng = MockEngine(bad_protocol)
        eng.log = MockLog()
        ctl = EngineController(eng)
        self.assertIn("Unrecognized protocol version", eng.log.warning)
        pos = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        ctl.newgame()
        ctl.setposition(pos)
        ctl.go()
        ctl.stop()
        ctl.quit()

    def test_controller(self):
        eng = MockEngine(protocol1)
        ctl = EngineController(eng)
        self.assertEqual(ctl.ident["name"], "Mock")
        self.assertEqual(ctl.ident["author"], "Janzert")
        self.assertEqual(ctl.protocol_version, 1)
        self.assertEqual(ctl.is_running(), True)
        self.assertRaises(socket.timeout, ctl.get_response)
        resp = ctl.get_response()
        self.assertIsInstance(resp, EngineResponse)
        self.assertEqual(resp.type, "log")
        self.assertEqual(resp.message,
                         eng.expected[eng.event - 1][1].split("log ", 1)[1])
        ctl.setoption("depth", 4)
        ctl.newgame()
        pos = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        ctl.setposition(pos)
        ctl.go()
        ctl.stop()
        resp = ctl.get_response()
        self.assertEqual(resp.type, "info")
        self.assertEqual(resp.message,
                         eng.expected[eng.event - 1][1].split("info ", 1)[1])
        resp = ctl.get_response()
        self.assertEqual(resp.type, "bestmove")
        self.assertEqual(resp.move,
                         eng.expected[eng.event - 1][1].split("bestmove ", 1)[1])
        ctl.makemove("Hb2n Ed2n")
        ctl.go("ponder")
        ctl.quit()
        ctl.cleanup()
        # bad response to isready
        eng = MockEngine(bad_isready_response)
        ctl = EngineController(eng)
        ctl.newgame()
        self.assertRaises(EngineException, ctl.isready)
        # timeout waiting for aeiok
        eng = MockEngine(aeiok_timeout)
        self.assertRaises(EngineException, EngineController, eng)
        # IOError sending aei
        eng = MockEngine(aei_send_error)
        self.assertRaises(EngineException, EngineController, eng)

    def _check_engine(self, eng):
        self.assertEqual(eng.is_running(), True)
        eng.send("aei\n")
        response = eng.waitfor("aeiok")
        self.assertEqual(response[-1], "aeiok")
        self.assertRaises(socket.timeout, eng.readline, timeout=0.05)
        eng.send("isready\n")
        response = eng.readline()
        self.assertEqual(response, "readyok")
        eng.send("quit\n")
        eng.waitfor("log")
        self.assertRaises(EngineException, eng.waitfor, "invalid", timeout=0.05)
        eng.cleanup()
        self.assertEqual(eng.active, False)

    def test_stdioengine(self):
        eng = aei.get_engine("stdio", "simple_engine")
        self.assertIsInstance(eng, aei.StdioEngine)
        self._check_engine(eng)
        eng = aei.get_engine("stdio", "simple_engine", "aei")
        self._check_engine(eng)

    def test_socketengine(self):
        path = os.path.dirname(__file__)
        adapter_path = os.path.join(path, "socketadapter.py")
        adapter_cmd = "%s %s" % (sys.executable, adapter_path)
        eng = aei.get_engine("socket", adapter_cmd)
        self.assertIsInstance(eng, aei.SocketEngine)
        self._check_engine(eng)
        eng = aei.get_engine("socket", adapter_cmd, "aei")
        self.assertIsInstance(eng, aei.SocketEngine)
        self._check_engine(eng)
        eng = aei.get_engine("2008cc", adapter_cmd + " --legacy")
        self._check_engine(eng)
