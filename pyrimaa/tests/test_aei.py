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

from pyrimaa.aei import EngineController

std_start = [("s", "aei"),
        ("r", "protocol-version 1"),
        ("r", "id name Mock"), ("r", "id author Janzert"),
        ("r", "aeiok"), ("s", "isready"), ("r", "readyok")]

class MockEngine:
    def __init__(self, expected):
        self.log = None
        self.expected = expected
        self.event = 0
        self._closed = False

    def __del__(self):
        if not self._closed:
            raise Exception("Mock engine abandoned without calling cleanup")

    def send(self, msg):
        if self._closed:
            raise Exception("Mock engine send called after cleanup.")
        expected = self.expected[self.event]
        if expected[0] != "s":
            raise Exception("Mock engine send called when expecting, %s" %
                    (expected, ))
        if msg.rstrip() != expected[1]:
            raise Exception("Mock engine send called with unexpected message (%s) expected (%s)." % (msg, expected[1]))
        self.event += 1

    def readline(self, timeout=None):
        if self._closed:
            raise Exception("Mock engine readline called after cleanup.")
        raise NotImplementedError("Mock readline not implemented")

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
            raise Exception("Mock engine waitfor called with unexpected message (%s)" % (msg, ))
        responses.append(expected[1])
        self.event += 1
        return responses

    def cleanup(self):
        if self._closed:
            raise Exception("Mock engine cleanup called multiple times.")
        self._closed = True

class EngineControllerTest(unittest.TestCase):
    def test_construction(self):
        eng = MockEngine(std_start)
        ctl = EngineController(eng)
        ctl.cleanup()
