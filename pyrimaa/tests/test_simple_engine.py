# Copyright (c) 2021 Brian Haskin Jr.
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

import re
import unittest
from subprocess import Popen, PIPE, STDOUT
try:
    from Queue import Queue, Empty
except:
    from queue import Queue, Empty


from pyrimaa import simple_engine


class MockController:
    def __init__(self):
        self.messages = Queue()
        self.eng_messages = list()
        class MockEvent:
            def __init__(self):
                self.stopped = False
            def is_set(self):
                return self.stopped
        self.stop = MockEvent()

    def send(self, msg):
        self.eng_messages.append(msg)

class EngineTest(unittest.TestCase):
    def test_aeiengine(self):
        ctl = MockController()
        ctl.messages.put("aei")
        eng = simple_engine.AEIEngine(ctl)
        self.assertEqual(len(ctl.eng_messages), 4)
        self.assertEqual(ctl.eng_messages[0], "protocol-version 1")
        self.assertTrue(ctl.eng_messages[1].startswith("id name"))
        self.assertTrue(ctl.eng_messages[2].startswith("id author"))
        self.assertEqual(ctl.eng_messages[3], "aeiok")

        ctl = MockController()
        def fake_get(timeout):
            raise Empty()
        ctl.messages.get = fake_get
        self.assertRaises(simple_engine.AEIException, simple_engine.AEIEngine, ctl)
        ctl = MockController()
        ctl.messages.put("badheader")
        self.assertRaises(simple_engine.AEIException, simple_engine.AEIEngine, ctl)

        ctl = MockController()
        send = [
            "aei",
            "isready",
            "go",
            "stop",
            "newgame",
            "setposition g [rrrrrrrrdhcemchd                               DDHCMECH RRRRRRRR]",
            "isready",
            "makemove Dh3n Dh4w Dg4n Dg5w",
            "go",
            "newgame",
            "setoption name delaymove value 0.2",
            "setoption name checkmoves value no",
            "setoption name unknown_option",
            "isready",
            "makemove Da2 Hb2 Cc2 Md2 Ee2 Cf2 Hg2 Dh2 Rb1 Rc1 Rd1 Re1 Rf1 Rg1",
            "makemove da7 hb7 cc7 md7 ee7 cf7 hg7 dh7 ra8 rb8 rc8 rd8 re8 rf8 rg8 rh8",
            "go",
            "newgame",
            "setoption name delaymove value 0",
            "isready",
            "makemove Ce5 Re4",
            "makemove hd4 cd5 ce6 df5 hf4",
            "go",
            "quit",
        ]
        for msg in send:
            ctl.messages.put(msg)
        eng = simple_engine.AEIEngine(ctl)
        eng.main()
        expected = [
            (r"protocol-version 1$", "protocol version"),
            (r"id name .+", "bot name"),
            (r"id author .+", "bot author"),
            (r"aeiok$", "aeiok"),
            (r"readyok$", "readyok"),
            (r"info time [\d]+$", "info time"),
            (r"bestmove .+", "bestmove"),
            (r"readyok$", "readyok"),
            (r"info time [\d]+$", "info time"),
            (r"bestmove( \w\w\d[nesw]( \w\w\dx)?){1,4}$", "bestmove"),
            (r"log Warning:", "log Warning"),
            (r"readyok$", "readyok"),
            (r"info time [\d]+$", "info time"),
            (r"bestmove( \w\w\d[nesw]( \w\w\dx)?){1,4}$", "bestmove"),
            (r"readyok$", "readyok"),
            (r"log Warning:", "log Warning"),
            (r"info time [\d]+$", "info time"),
            (r"bestmove $", "blank bestmove"),
            (r"log .+", "log"),
            (r"info move gen time .+", "info move gen time")
        ]
        for response, (pattern, exp_msg) in zip(ctl.eng_messages, expected):
            self.assertTrue(
                re.match(pattern, response),
                "Expected %s message got %s" % (exp_msg, response)
            )
        self.assertEqual(
            len(ctl.eng_messages), len(expected),
            "Unexpected number of responses"
        )

        ctl = MockController()
        send = [
            "aei",
            "isready",
            "makemove Da2 Hb2 Cc2 Md2 Ee2 Cf2 Hg2 Dh2 Rb1 Rc1 Rd1 Re1 Rf1 Rg1",
        ]
        for msg in send:
            ctl.messages.put(msg)
        eng = simple_engine.AEIEngine(ctl)
        eng.main()
        expected = [
            (r"protocol-version 1$", "protocol version"),
            (r"id name .+", "bot name"),
            (r"id author .+", "bot author"),
            (r"aeiok$", "aeiok"),
            (r"readyok$", "readyok"),
            (r"log Error:", "log Error")
        ]
        for response, (pattern, exp_msg) in zip(ctl.eng_messages, expected):
            self.assertTrue(
                re.match(pattern, response),
                "Expected %s message got %s" % (exp_msg, response)
            )
        self.assertEqual(
            len(ctl.eng_messages), len(expected),
            "Unexpected number of responses"
        )

    def test_script(self):
        cmdline = "python -m pyrimaa.simple_engine"
        proc = Popen(cmdline.split(), stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        proc.stdin.write(b"aei\n")
        proc.stdin.write(b"isready\n")
        proc.stdin.write(b"quit\n")
        expected = [
            (r"protocol-version 1$", "protocol version"),
            (r"id name .+", "bot name"),
            (r"id author .+", "bot author"),
            (r"aeiok$", "aeiok"),
            (r"readyok$", "readyok"),
            (r"log Debug:", "log Debug")
        ]
        response, _ = proc.communicate()
        response_lines = response.decode("utf-8").splitlines()
        for line, (pattern, exp_msg) in zip(response_lines, expected):
            self.assertTrue(
                re.match(pattern, line),
                "Expected %s message got %s" % (exp_msg, line)
            )
        self.assertEqual(len(response_lines), len(expected))
