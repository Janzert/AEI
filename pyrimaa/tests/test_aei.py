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

import unittest

from pyrimaa import board
from pyrimaa.aei import EngineController, EngineResponse


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
                            (expecting, ))
        self.event += 1
        return expected[1]

    def waitfor(self, msg, timeout=0.5):
        if self._closed:
            raise Exception("Mock engine waitfor called after cleanup.")
        msg = msg.rstrip()
        expected = self.expected[self.event]
        if expected[0] != "r":
            raise Exception("Mock engine waitfor called when expecting, %s" %
                            (expected, ))
        responses = []
        while expected[0] == "r" and expected[1] != msg:
            responses.append(expected[1])
            self.event += 1
            expected = self.expected[self.event]
        if expected[0] != "r" or msg != expected[1]:
            raise Exception(
                "Mock engine waitfor called with unexpected message (%s)" %
                (msg, ))
        responses.append(expected[1])
        self.event += 1
        return responses

    def cleanup(self):
        if self._closed:
            raise Exception("Mock engine cleanup called multiple times.")
        self._closed = True


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

protocol1 = [
    ("s", "aei"),
    ("r", "protocol-version 1"),
    ("r", "id name Mock"),
    ("r", "id author Janzert"),
    ("r", "aeiok"),
    ("s", "isready"),
    ("r", "readyok"),
    ("r", "log Engine running"),
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


class EngineControllerTest(unittest.TestCase):
    def test_controller_protocol0(self):
        eng = MockEngine(protocol0)
        ctl = EngineController(eng)
        self.assertEqual(ctl.ident["name"], "Mock0")
        self.assertEqual(ctl.ident["author"], "Janzert")
        self.assertEqual(ctl.protocol_version, 0)
        ctl.newgame()
        pos = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        ctl.setposition(pos)
        ctl.cleanup()

    def test_controller_protocol1(self):
        eng = MockEngine(protocol1)
        ctl = EngineController(eng)
        self.assertEqual(ctl.ident["name"], "Mock")
        self.assertEqual(ctl.ident["author"], "Janzert")
        self.assertEqual(ctl.protocol_version, 1)
        self.assertEqual(ctl.is_running(), True)
        resp = ctl.get_response()
        self.assertIsInstance(resp, EngineResponse)
        self.assertEqual(resp.type, "log")
        self.assertEqual(resp.message,
                         eng.expected[eng.event - 1][1].lstrip("log "))
        ctl.setoption("depth", 4)
        ctl.newgame()
        pos = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        ctl.setposition(pos)
        ctl.go()
        ctl.stop()
        resp = ctl.get_response()
        self.assertEqual(resp.type, "info")
        self.assertEqual(resp.message,
                         eng.expected[eng.event - 1][1].lstrip("info "))
        resp = ctl.get_response()
        self.assertEqual(resp.type, "bestmove")
        self.assertEqual(resp.move,
                         eng.expected[eng.event - 1][1].lstrip("bestmove "))
        ctl.makemove("Hb2n Ed2n")
        ctl.go("ponder")
        ctl.quit()
        ctl.cleanup()
