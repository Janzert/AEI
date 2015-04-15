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

import os
import StringIO
import sys
import unittest

from contextlib import contextmanager
from tempfile import NamedTemporaryFile

from pyrimaa import analyze


@contextmanager
def get_temps(num=1):
    tmps = list()
    for i in range(num):
        tmps.append(NamedTemporaryFile(delete=False))
    try:
        yield tmps
    finally:
        for tmp in tmps:
            os.remove(tmp.name)


@contextmanager
def save_stdio():
    org_stdin = sys.stdin
    org_stdout = sys.stdout
    org_stderr = sys.stderr
    try:
        yield
    finally:
        sys.stdin = org_stdin
        sys.stdout = org_stdout
        sys.stderr = org_stderr


test_config = """
[global]
default_engine = bot_simple

[bot_simple]
cmdline = simple_engine
"""

basic_pos = """
3w
 +-----------------+
8| r r r r r r r r |
7| h   c   e c h d |
6| d   X   m X     |
5|                 |
4|         E       |
3|     X   R X     |
2| H D C M   C D H |
1| R R R R   R R R |
 +-----------------+
   a b c d e f g h
"""


class AnalyzeTest(unittest.TestCase):
    def test_main(self):
        with get_temps(2) as (cfg, pos):
            cfg.write(test_config)
            cfg.close()
            pos.write(basic_pos)
            pos.close()
            with save_stdio():
                out = StringIO.StringIO()
                err = StringIO.StringIO()
                sys.stdout, sys.stderr = out, err
                ret = analyze.main(["--config", cfg.name, pos.name])
            self.assertEqual(ret, 0)
            self.assertIn("bestmove: ", out.getvalue())
            self.assertEqual(len(err.getvalue()), 0)
