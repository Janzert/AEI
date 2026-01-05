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

import logging
import os
import sys
import unittest
from io import StringIO
from importlib import reload

from contextlib import contextmanager
from tempfile import NamedTemporaryFile

from pyrimaa import aei, analyze, board


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
        out = StringIO()
        err = StringIO()
        sys.stdout, sys.stderr = out, err
        logging.shutdown()
        reload(logging)
        analyze.logging = logging
        analyze.log = logging.getLogger("analyze")
        yield (out, err)
    finally:
        sys.stdin = org_stdin
        sys.stdout = org_stdout
        sys.stderr = org_stderr
        out.close()
        err.close()


test_config = b"""
[global]
default_engine = bot_simple

[bot_simple]
cmdline = simple_engine
bot_checkmoves = false
"""

badlog_cfg = b"""\
[global]
default_engine = bot_simple
log_level = UNKNOWN_LEVEL

[bot_simple]
cmdline = simple_engine
"""

goodlog_cfg = b"""\
[global]
default_engine = bot_simple
log_level = DEBUG

[bot_simple]
cmdline = simple_engine
"""

badbot_cfg = b"""\
[global]
default_engine = bot_simplydone

[bot_simple]
cmdline = simple_engine
"""

nocmd_cfg = b"""\
[global]
default_engine = bot_simple

[bot_simple]
"""

badcmd_cfg = b"""\
[global]
default_engine = bot_simple

[bot_simple]
cmdline = nonexistantbotcommand
"""

botoptions_cfg = b"""\
[global]
default_engine = bot_simple
log_level = DEBUG

[bot_simple]
cmdline = simple_engine
bot_nonoption = test
bot_another = 2
post_pos_afteroption = afterpos
post_pos_aftertwo = 42
"""

delaymove_cfg = b"""\
[global]
default_engine = bot_simple

[bot_simple]
cmdline = simple_engine
bot_delaymove = 1
"""

nosearch_cfg = b"""\
[global]
default_engine = bot_simple
search_position = no

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

basic_pos_short = "[rrrrrrrrh c echdd   m           "\
                   "    E       R   HDCM CDHRRRR RRR]"

basic_movelist = """\
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

movelist_2s_short = "[rrrcdrrrrhdhecmr            E   "\
                     "                HMD DCHRRRCRRRRR]"

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

movelist_4g_short = "[rrrc rrrr dhdcmrHh       e  E   "\
                     "                 MD DCHRRRCRRRRR]"

illegal_moves = """\
1g Ra1 Rb1 Cc1 Rd1 Re1 Rf1 Rg1 Rh1 Ha2 Mb2 Dc2 Ed2 De2 Cf2 Hg2 Rh2
1s ra7 hb7 dc7 hd7 ee7 cf7 mg7 rh7 ra8 rb8 rc8 cd8 de8 rf8 rg8 rh8
2g Ed2n Ed3n Ed4n Ed5e
2s hb7s ee7s de8s ee6w
3g Ee5w Ed5w hb6s
"""

illegal_setup = """\
1g Ra1 Rb1 Cc1 Rd1 Re1 Rf1 Rg1 Rh1 Ha2 Mb2 Dc2 Ee3 De2 Cf2 Hg2 Rh2
1s ra7 hb7 dc7 hd7 ed6 cf7 mg7 rh7 ra8 rb8 rc8 cd8 de8 rf8 rg8 rh8
"""

class FastTimeoutCom(aei._ProcCom):
    _original_procom = aei._ProcCom

    def __init__(self, proc, log):
        self._original_procom.__init__(self, proc, log)
        self._original_outq_get = self.outq.get
        self.outq.get = self._fast_timeout_get
        self.get_called = 0
        self.ignore = 2

    def _fast_timeout_get(self, block=True, timeout=None):
        self.get_called += 1
        if timeout and self.get_called > 2: # don't shorten first calls
            timeout = min(timeout, 0.2)
        return self._original_outq_get(block, timeout)


class AnalyzeTest(unittest.TestCase):
    def test_parse_start(self):
        prelines = ["This is just other text before the position or",
                    "movelist that should be thrown out before parsing"]
        # check handling if no move or board given
        self.assertRaises(analyze.ParseError, analyze.parse_start, prelines)
        # check board parsing with and without extra lines before
        pos = board.parse_short_pos(board.Color.GOLD, 4, basic_pos_short)
        lines = prelines + basic_pos.splitlines()
        got_board, start = analyze.parse_start(lines)
        self.assertEqual(got_board, True)
        self.assertEqual(start, pos)
        lines = basic_pos.splitlines()
        got_board, start = analyze.parse_start(lines)
        self.assertEqual(got_board, True)
        self.assertEqual(start, pos)
        # check movelist parsing
        lines = prelines + basic_movelist.splitlines()
        got_board, start = analyze.parse_start(lines)
        self.assertEqual(got_board, False)
        self.assertEqual(start, lines[2:])
        lines = basic_movelist.splitlines()
        got_board, start = analyze.parse_start(lines)
        self.assertEqual(got_board, False)
        self.assertEqual(start, lines)
        # check stopping early in a movelist
        lines = basic_movelist.splitlines()
        got_board, start = analyze.parse_start(lines, "2s")
        self.assertEqual(got_board, False)
        self.assertEqual(start, lines[:3])

    def test_config(self):
        # missing config file
        with save_stdio() as (out, err):
            ret = analyze.main(["--config", "nonexistantfilename", "posfile"])
        self.assertGreater(ret, 0)
        with get_temps(2) as (cfg, pos):
            # bad log level
            pos.write(basic_pos.encode("utf-8"))
            pos.close()
            cfg.write(badlog_cfg)
            cfg.flush()
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, pos.name])
                stdout = out.getvalue()
            self.assertIn("Bad log level \"Level UNKNOWN_LEVEL\", use ", stdout)
            self.assertGreater(ret, 0)
            # good log level
            cfg.seek(0)
            cfg.truncate(0)
            cfg.write(goodlog_cfg)
            cfg.flush()
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, pos.name])
                stderr = err.getvalue()
            self.assertEqual(ret, 0)
            self.assertIn("DEBUG:analyze.aei:", stderr)
            # bad bot name
            cfg.seek(0)
            cfg.truncate(0)
            cfg.write(badbot_cfg)
            cfg.flush()
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, pos.name])
                stdout = out.getvalue()
            self.assertGreater(ret, 0)
            self.assertIn("configuration for bot_simplydone", stdout)
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, pos.name,
                                    "--bot", "bot_simple"])
            self.assertEqual(ret, 0)
            # missing bot command
            cfg.seek(0)
            cfg.truncate(0)
            cfg.write(nocmd_cfg)
            cfg.flush()
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, pos.name])
                stdout = out.getvalue()
            self.assertGreater(ret, 0)
            self.assertIn("No engine command line found", stdout)
            # bad bot command
            cfg.seek(0)
            cfg.truncate(0)
            cfg.write(badcmd_cfg)
            cfg.flush()
            default_start_time = aei.START_TIME
            aei.START_TIME = 0.1
            try:
                with save_stdio() as (out, err):
                    ret = analyze.main(["--config", cfg.name, pos.name])
                    stdout = out.getvalue()
            finally:
                aei.START_TIME = default_start_time
            self.assertGreater(ret, 0)
            self.assertIn("Bot probably did not start", stdout)
            # bot options
            cfg.seek(0)
            cfg.truncate(0)
            cfg.write(botoptions_cfg)
            cfg.flush()
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, pos.name])
                stdout = out.getvalue()
            self.assertEqual(ret, 0)
            self.assertIn("Warning: Received unrecognized option, nonoption",
                          stdout)
            self.assertIn("Warning: Received unrecognized option, another",
                          stdout)
            self.assertIn("Warning: Received unrecognized option, afteroption",
                          stdout)
            self.assertIn("Warning: Received unrecognized option, aftertwo",
                          stdout)
            # monkey patch aei._ProcCom to force fast communication timeouts
            real_ProcCom = aei._ProcCom
            try:
                aei._ProcCom = FastTimeoutCom
                # ensure default is search position enabled and works
                cfg.seek(0)
                cfg.truncate(0)
                cfg.write(delaymove_cfg)
                cfg.flush()
                with save_stdio() as (out, err):
                    ret = analyze.main(["--config", cfg.name, pos.name])
                    stdout = out.getvalue()
                self.assertEqual(ret, 0)
                self.assertIn("bestmove:", stdout)
                # disable search position
                cfg.seek(0)
                cfg.truncate(0)
                cfg.write(nosearch_cfg)
                cfg.flush()
                with save_stdio() as (out, err):
                    ret = analyze.main(["--config", cfg.name, pos.name])
                    stdout = out.getvalue()
                self.assertEqual(ret, 0)
                self.assertNotIn("bestmove:", stdout)
            finally:
                cfg.close()
                aei._ProcCom = real_ProcCom

    def test_board(self):
        with get_temps(2) as (cfg, pos):
            # basic board
            cfg.write(test_config)
            cfg.close()
            pos.write(basic_pos.encode("utf-8"))
            pos.flush()
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, pos.name])
                stdout, stderr = out.getvalue(), err.getvalue()
            self.assertEqual(ret, 0)
            self.assertIn("bestmove: ", stdout)
            print(stderr)
            self.assertEqual(len(stderr), 0)
            # not a board or move list
            pos.seek(0)
            pos.truncate(0)
            pos.write(b"no board or moves")
            pos.close()
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, pos.name])
                stdout = out.getvalue()
            self.assertIn("does not appear to be a board", stdout)

    def test_movelist(self):
        with get_temps(2) as (cfg, movelist):
            cfg.write(test_config)
            cfg.close()
            movelist.write(basic_movelist.encode("utf-8"))
            movelist.close()
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, movelist.name])
                stdout, stderr = out.getvalue(), err.getvalue()
            self.assertEqual(ret, 0)
            self.assertIn("bestmove: ", stdout)
            self.assertIn(movelist_4g, stdout)
            print(stderr)
            self.assertEqual(len(stderr), 0)
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, movelist.name, "2s"])
                stdout, stderr = out.getvalue(), err.getvalue()
            self.assertEqual(ret, 0)
            self.assertIn("bestmove: ", stdout)
            self.assertIn(movelist_2s, stdout)
            self.assertEqual(len(stderr), 0)

    def test_movechecks(self):
        with get_temps(2) as (cfg, pos):
            cfg.write(test_config)
            cfg.close()
            pos.write(illegal_moves.encode("utf-8"))
            pos.flush()
            # with strict checks
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, pos.name,
                                    "--strict-checks"])
                stdout = out.getvalue()
            self.assertGreater(ret, 0)
            self.assertIn("Enabling full legality checking on moves", stdout)
            self.assertIn("Illegal move found", stdout)
            # without strict checks
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, pos.name,
                                    "--skip-checks"])
                stdout = out.getvalue()
            self.assertEqual(ret, 0)
            self.assertNotIn("Illegal move found", stdout)
            # illegal setup
            pos.seek(0)
            pos.truncate(0)
            pos.write(illegal_setup.encode("utf-8"))
            pos.close()
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, pos.name,
                                    "--strict-setup"])
                stdout = out.getvalue()
            self.assertGreater(ret, 0)
            self.assertIn("Enabling full legality checking on setup", stdout)
            self.assertIn("Tried to place a piece outside", stdout)
            with save_stdio() as (out, err):
                ret = analyze.main(["--config", cfg.name, pos.name,
                                    "--allow-setup"])
                stdout = out.getvalue()
            self.assertEqual(ret, 0)
            self.assertIn("Disabling full legality checking on setup", stdout)

