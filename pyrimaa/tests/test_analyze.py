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

basic_movelist = """
1g Ra1 Rb1 Cc1 Rd1 Re1 Rf1 Rg1 Rh1 Ha2 Mb2 Dc2 Ed2 De2 Cf2 Hg2 Rh2
1s ra7 hb7 dc7 hd7 ee7 cf7 mg7 rh7 ra8 rb8 rc8 cd8 de8 rf8 rg8 rh8
2g Ed2n Ed3n Ed4n Ed5e
2s hb7s ee7s de8s ee6w
3g Ha2n Ha3n Ha4n Ha5n
3s ed6s ed5w ec5w
"""

movelist_2s = """ +-----------------+
8| r r r c d r r r |
7| r h d h e c m r |
6| . . x . . x . . |
5| . . . . E . . . |
4| . . . . . . . . |
3| . . x . . x . . |
2| H M D . D C H R |
1| R R C R R R R R |
 +-----------------+
   a b c d e f g h"""

movelist_4g = """ +-----------------+
8| r r r c . r r r |
7| r . d h d c m r |
6| H h x . . x . . |
5| . e . . E . . . |
4| . . . . . . . . |
3| . . x . . x . . |
2| . M D . D C H R |
1| R R C R R R R R |
 +-----------------+
   a b c d e f g h"""


class AnalyzeTest(unittest.TestCase):
    def test_board(self):
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

    def test_movelist(self):
        with get_temps(2) as (cfg, movelist):
            cfg.write(test_config)
            cfg.close()
            movelist.write(basic_movelist)
            movelist.close()
            with save_stdio():
                out = StringIO.StringIO()
                err = StringIO.StringIO()
                sys.stdout, sys.stderr = out, err
                ret = analyze.main(["--config", cfg.name, movelist.name])
            self.assertEqual(ret, 0)
            self.assertIn("bestmove: ", out.getvalue())
            self.assertIn(movelist_4g, out.getvalue())
            self.assertEqual(len(err.getvalue()), 0)
            with save_stdio():
                out = StringIO.StringIO()
                err = StringIO.StringIO()
                sys.stdout, sys.stderr = out, err
                ret = analyze.main(["--config", cfg.name, movelist.name, "2s"])
            self.assertEqual(ret, 0)
            self.assertIn("bestmove: ", out.getvalue())
            self.assertIn(movelist_2s, out.getvalue())
            self.assertEqual(len(err.getvalue()), 0)
