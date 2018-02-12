# Copyright (c) 2010 Brian Haskin Jr.
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

import socket
import time
import unittest

from collections import defaultdict

import pyrimaa.game
from pyrimaa.board import Color, Position, BASIC_SETUP, IllegalMove
from pyrimaa.game import Game
from pyrimaa.util import TimeControl

goal_moves = """1g Ra2 Db2 Hc2 Ed2 Me2 Hf2 Dg2 Rh2 Ra1 Rb1 Rc1 Cd1 Ce1 Rf1 Rg1 Rh1
1s rh7 ra7 rh8 rg8 rf8 rc8 rb8 ra8 cc7 cd8 df7 de8 hg7 hb7 md7 ee7
2g Ed2n Ed3n Ed4n Dg2n
2s ee7s ee6s ee5s ee4s
3g Db2n Hf2e Me2e Ce1n
3s ee3w Ce2n Ce3n ed3e
4g Ed5e Cd1n Ee5n Cd2e
4s hg7s de8s df7e de7e
5g Ee6w Ed6s md7s
5s cd8s md6w mc6w cd7e
6g Ed5e Ce4w Cd4w Ee5s
6s ee3w Ce2n Ce3e ed3e
7g Mf2w Cf3s Cc4s Cc3e
7s Cd3n ee3w Cd4n ed3n
8g Ee4n Cd5n Ee5w Cd6n
8s ed4s ce7n df7w ce8w
9g Ed5n Ed6e Ee6s de7s
9s cc7s cc6e ed3s hb7e
10g Ee5w de6s de5s Ed5e
10s mb6s ra7e hg6e mb5s
11g de4s Ee5s Ee4w Ed4w
11s ed2n de3n de4w rf8w
12g Ec4n dd4w dc4s Ec5s
12s rb7w ra7s ra6s ra5s
13g Ra2e Db3w Da3e ra4s
13s rb8s rb7s rb6s mb4w
14g Ec4n Rb2w Ec5s rb5e
14s cd6s rc5w hh6w cd5n
15g Ec4n Ec5s rb5e Me2s
15s hg6s hg5s Dg3e hg4s
16g rc5n Ec4n Ec5s
16s rc6s
17g rc5n Ec4n Ec5s
17s dg7s rc6w rh7w rb6s
18g Ec4n Ec5s rb5e Dh3n
18s hg3n hg4s Dh4w dg6s
19g Ec4w Eb4e ma4e Ra2e
19s cd6s rc5w mb4w Db3n
20g rb5e Db4n Db5s Db4s
20s ra3s ma4s Db3n ma3e
21g Db4w Ec4w Eb4e mb3n
21s rc5w mb4s mb3w dc3w
22g Ec4w db3e Eb4s
22s hc7w Cd7w Cc7s Cc6x hb7e
23g Me1n Me2n Cf2w Rf1n
23s rg7w dc3n Me3n ed3e
24g Hc2n Hc3e dc4s dc3x Rb2e
24s hg3w rb5e hf3e Rf2n Rf3x
25g Eb3e ma3e Ec3n mb3e mc3x
25s ee3e Me4s ef3n Me3e Mf3x
26g Ec4e Ce2n Hg2w Ed4e
26s cd5n cd6n dg5e dh5s
27g Rc1e Da4s Da3e ra2n
27s hg3w hf3e Ce3e rf7e
28g Db3e ra3e Dc3n rb3e rc3x
28s hc7s cd7w rc5w hc6s
29g Hd3n Dc4w Db4s rb5s
29s hc5w rb4w cc7w hb5w
30g Db3n Cf3w Db4s ra4e
30s ha5e rb4w hb5w rg8w
31g Hd4w Hc4w Hb4n ra4e
31s cb7s ha5s ha4s rc8s
32g rb4e Hb5s rc4s rc3x Hb4e
32s ha3s ha2e Ra1n cb6n
33g Hc4n Hc5w Rd1w Hb5n
33s cb7n rc7w rb7w cb8e
34g Hb6n Hb7e Hc7e cc8s
34s cd8w cc8w ra7e rb7s
35g Hd7n cc7e cd7e Hd8s
35s ce7e rg7s rf8e cb8s
36g Rc2n Rc3n Hd7w
36s cf7w ra8e re8w rb8e
37g cb7w Hc7w rb6e rc6x Hb7s
37s ce7w rc8s rg6s cd7s
38g Rb1w Ra2n Ra3n Ra4n
38s Db3w hb2n hb3n hb4w
39g Ee4n Ee5w cd6e Ed5n
39s ef4w Ce3w ee4s
40g Ed6w Rc4n Ec6e rc7s rc6x
40s ha4e Ra5s rd8w hb4n
41g Ed6s Rc5n Rc6n Ed5e
41s rg8w rf8w ca7e re8w
42g Ra4n Da3n Ra5n Ra6n
42s rh8w hb5w ha5n Da4n
43g cb7n Hb6n Ra7n"""
goal_moves = goal_moves.splitlines()

resign_moves = """1g Ra2 Db2 Hc2 Ed2 Me2 Hf2 Dg2 Rh2 Ra1 Rb1 Rc1 Cd1 Ce1 Rf1 Rg1 Rh1
1s rh7 ra7 rh8 rg8 rf8 rc8 rb8 ra8 cc7 cd8 df7 de8 hg7 hb7 md7 ee7
2g Ed2n Ed3n Ed4n Dg2n
2s resign"""
resign_moves = resign_moves.splitlines()

immo_moves = """1g Rh1 Rg1 Rf1 Rc1 Rb1 Ra1 Rh2 Ra2 Cd1 Cf2 De1 Dc2 Hg2 Hb2 Md2 Ee2
1s ra7 hb7 dc7 ed7 me7 df7 hg7 rh7 ra8 rb8 rc8 cd8 ce8 rf8 rg8 rh8
2g Ee2n Ee3n Ee4n Ee5n
2s ed7s me7w hg7s ed6s
3g Hb2n Dc2n Ee6w Md2w
3s hb7s dc7w md7w cd8s
4g Mc2w Ed6e cd7s Dc3s
4s rh7s cd6n ed5w ec5s
5g De1n Ee6n df7e Ee7e
5s rh8s ec4w eb4e Hb3n
6g Mb2n Hb4w Ha4s Cd1n
6s ce8s ec4w eb4w Mb3n
7g Ha3e Mb4e Hb3s Mc4s
7s rf8w hb6e hc6e hd6e
8g Hg2n Hg3n Hg4n Mc3e
8s cd7s mc7e he6e cd6e
9g Hg5w Hf5w He5e ce6s
9s md7s md6s ce5n md5e
10g Md3e Me3n Rc1e Rd1e
10s rc8e db7e dc7e ea4e
11g Me4e Hf5e Ef7n Hg5s
11s ce7e dd7e me5s me4s
12g Mf4n Re1w Hg4s Rh2w
12s eb4e ec4e ed4e ee4e
13g Hg3n Rg2n Hg4n Mf5w
13s rg8e dg7n hg6n ef4n
14g Hb2n Hb3n Hb4n Hb5n
14s me3n me4w md4n md5w
15g Hb6n Cd2n De2n Rg3n
15s ce6w cd6n mc5w mb5n
16g Cd3n Hg5e Cd4n Me5s
16s mb6s Hb7s Hb6e Hc6x mb5n
17g Hh5s Cd5s Cd4s
17s mb6s ef5s Me4n ef4w
18g Hh4n Hh5w Cd3n Hg5n
18s Me5w ee4n Md5n ee5w
19g De3w Cd4e Ce4e Cf4s
19s Md6w Mc6x ed5n ed6e ee6s
20g Hg6s Cf3e Hg5e Ra2e
20s ee5e ef5s Rg4n ef4e
21g rh6w Hh5n Rb1e Rf1w
21s hf6s rg6w Rg5n eg4n
22g Rg1w Rh1w Dd3e Hh6s
22s rb8e hf5s mb5s mb4s
23g Dc2e Rc1w Rb2e De3w
23s rf6w Rg6w Rf6x eg5n re6e
24g Re1n Rd1w Hh5s Hh4s
24s cd7w ra7s ra6s ra5s
25g Cg3s Hh3w Hg3w Hf3w
25s hf4w he4w Dd3w hd4s
26g Cg2e Ch2s Dc3n He3n
26s eg6s eg5w hd3n mb3n
27g Rc2w He4s Dd2n Rc1n
27s Dc4n mb4e hd4n Dd3n
28g Re2w He3w Dd4e De4s
28s rc8w ef5s ra4s ra3s
29g Rd2e Hd3s Hd2s Hd1w
29s Dc5n Dc6x hd5w mc4w mb4s
30g De3w Rc2n Rf1w Rb2e
30s ef4w ee4s Dd3n ee3w
31g Rc3n Dd4e De4e Cf2e
31s ed3e ee3n Df4s Df3x ee4e
32g Re2n Re3w
32s hc5e Rc4n Rc5n Rc6x hd5w
33g Rc2n Re1w Rg1w Hc1n
33s hc5s hc4e Rc3n mb3s
34g Rf1n Rf2w Re2w
34s Hc2s mb2e Rc4n hd4w
35g Rd2e Rb1n Hc1w Rd1w
35s ef4w ee4w Rd3w Rc3x ed4s
36g Cg2e Ch1w Rc1e Cg1w
36s hc4s Rc5s hc3w Rc4s Rc3x
37g Rd1w Cf1w Ch2s Ce1w
37s mc2e Rc1n Rc2n Rc3x md2w
38g Ch1n Re2w Cd1w Ch2n
38s ed3n Rd2n Rd3w Rc3x ed4s
39g Ch3w Cg3s
39s hb3n Rb2n Rb3e Rc3x hb4s
40g Hb1n Ra1e ra2n Hb2w
40s hb3n mc2w Cc1n ed3s
41g Cg2s Cg1e
41s ed2e ee2e ef2e eg2s"""
immo_moves = immo_moves.splitlines()

elim_moves = """1g Ra1 Rb1 Rc1 Cd1 Re1 Rf1 Dg1 Rh1 Ra2 Db2 Mc2 Cd2 Ee2 Hf2 Hg2 Rh2
1s ed7 mg7 he7 df7 ce8 hb7 dc7 cd8 ra7 rh7 ra8 rb8 rc8 rf8 rg8 rh8
2g Ee2n Hg2n Dg1n Ee3w
2s ed7s ed6s ed5s mg7s
3g Ed3e Ee3n Ee4n Ee5n
3s ed4s Cd2e ed3s hb7s
4g Ee6w he7s Db2n Hg3n
4s mg6s mg5n Hg4n rb8s
5g Db3e he6s Ed6e Dc3e
5s Dd3n ed2n rg8s cd8s
6g Cd1n Mc2w Mb2n Cd2w
6s ed3e ee3n he5e ee4n
7g Mb3n Mb4n hb6w Mb5n
7s ee5w ed5w ec5w cd7s
8g Dd4n Ce2w cd6w Dd5n
8s ha6s ha5s Mb6w eb5n
9g Dd6s Dd5s Dd4s Ra2e
9s dc7e cc6n hf5s hf4e
10g Rb2w Cc2n Cc3n Cc4n
10s eb6e ec6w Cc5n Cc6x ha4e
11g Cd2w Dd3n Dd4n Dd5w
11s eb6e ec6w Dc5n Dc6x hb4s
12g Ee6n Ee7s df7w Ee6w
12s mg6e Hg5n Hg6w Hf6x mh6w
13g Ed6e Ee6w de7s Cc2e
13s dd7e de7e hg4s hb3s
14g Ed6n Rc1e cc7s Ed7w
14s ce8w cc6e cd6n de6w
15g rc8w Ec7n Ec8s Rb1e
15s df7w rf8w cd8w re8w
16g Cd2w Rf1e Cc2e Cd2e
16s rg7w de7s rf7w rh8w
17g Ce2w Hf2s Hf1n Re1e
17s rg8w rf8s mg6s rh7s
18g Cd2w Rd1e Cc2e Cd2e
18s mg5w mf5s hb2e hc2e
19g Ce2n Hf2w Dg2w Rh2w
19s mf4s Ce3n mf3w de6s
20g Rg2e Rc1e Df2e Rf1n
20s me3e mf3w Rf2n Rf3x de5e
21g Ra2e Rg1w Rf1n Rb2w
21s me3e mf3w Rf2n Rf3x
22g Dg2s Rh2w Rg2w Dg1w
22s hg3w hf3e Rf2n Rf3x df5w
23g Rh1n Df1e Rh2w Rg2w
23s hg3s Rf2n Rf3x hg2w
24g Dg1e Dh1n Dh2n Dh3w
24s me3e mf3w Dg3w Df3x rh6s
25g Ec7s Ec6x cc8s
25s me3w He2n He3e Hf3x md3e
26g Rd1w Re1n
26s me3w Re2n Re3e Rf3x md3e
27g Rc1n
27s Rc2n Rc3x hd2w eb6s Ma6e
28g Ra2e
28s Rb2n hc2w Rb3e Rc3x hb2n
29g Ra1e
29s de5n de6e df6e hb3w
30g Rb1e
30s Mb6e Mc6x eb5n dd6e me3w
31g Ce4e Cf4e Cg4e Rc1w
31s ha3e hb3s hb2n Rb1n
32g Ch4s rh5s rh4w Ch3n
32s Rb2e hb3s Rc2n Rc3x hb2e"""
elim_moves = elim_moves.splitlines()

handicap_moves = """1g Rc2 Ee5
1s rc7 rf7 ed7
2g Ee5n Ee6n rf7s rf6x Ee7e
2s ed7s rc7s rc6s rc5s
3g Rc2n Rc3x"""
handicap_moves = handicap_moves.splitlines()

extra_step_moves = """1g Ra1 Rb1 Rc1 Cd1 Re1 Rf1 Dg1 Rh1 Ra2 Db2 Mc2 Cd2 Ee2 Hf2 Hg2 Rh2
1s ed7 mg7 he7 df7 ce8 hb7 dc7 cd8 ra7 rh7 ra8 rb8 rc8 rf8 rg8 rh8
2g Ee2n Hg2n Dg1n Ee3w
2s ed7s ed6s ed5s mg7s
3g Ed3e Ee3n Ee4n Ee5e ed4w
3s ra7s ra6s ra5s"""
extra_step_moves = extra_step_moves.splitlines()

repetition_moves = """1g Ra1 Rb1 Rc1 Cd1 Re1 Rf1 Dg1 Rh1 Ra2 Db2 Mc2 Cd2 Ee2 Hf2 Hg2 Rh2
1s ed7 mg7 he7 df7 ce8 hb7 dc7 cd8 ra7 rh7 ra8 rb8 rc8 rf8 rg8 rh8
2g Ee2n Ee3n Ee4n
2s ed7s ra7s ra6e rb6s
3g Ee5n Ee6s he7s
3s he6n
4g Ee5n Ee6s he7s
4s he6n
5g Ee5n Ee6s he7s
5g he6n
6g Ee5n Ee6s he7s
6s he6n
7g Ra2n Ra3n Ra4n Ra5n
7s ra8s hb7s hb6e ra7e
8g Ra6n Ra7n"""
repetition_moves = repetition_moves.splitlines()

null_moves = """1g Ra1 Rb1 Rc1 Cd1 Re1 Rf1 Dg1 Rh1 Ra2 Db2 Mc2 Cd2 Ee2 Hf2 Hg2 Rh2
1s ed7 mg7 he7 df7 ce8 hb7 dc7 cd8 ra7 rh7 ra8 rb8 rc8 rf8 rg8 rh8
2g Ee2n Ee3n Ee4n
2s ra7s ra6e rb6s
3g Ee5n Ee6w Ed6s Ed5e
3s rb5w"""
null_moves = null_moves.splitlines()


class MockResponse(object):
    def __init__(self, msg_type="bestmove"):
        self.type = msg_type


class MockEngine(object):
    def __init__(self, delay=None, moves=goal_moves, isready=[]):
        self.moves = moves
        self.delay = delay
        self.protocol_version = 1
        self.isready_resp = isready
        self.stopCount = 0
        self.stopMove = None
        self.curtime = 10
        self.ident = {"name": "Mock Engine", "author": "Mocker"}
        self.options_set = defaultdict(list)

    def _time(self):
        return self.curtime

    def setoption(self, opt, val):
        self.options_set[opt].append(val)

    def setposition(self, pos):
        pass

    def makemove(self, move):
        cur_move = self.moves[self.move].split()[1:]
        cur_move = " ".join(cur_move)
        if move != cur_move:
            raise ValueError("Moves did not match: %s %s" % (move, cur_move))

    def newgame(self):
        self.move = -3

    def isready(self):
        return self.isready_resp

    def go(self):
        pass

    def stop(self):
        self.stopCount += 1
        self.stopMove = self.move

    def get_response(self, timeout=None):
        self.move += 1
        if self.move == -2:
            resp = MockResponse("info")
            resp.message = "Test info message"
        elif self.move == -1:
            resp = MockResponse("log")
            resp.message = "Test log message"
        else:
            if self.move >= len(self.moves):
                raise ValueError("Game not stopped before end of moves")
            move = self.moves[self.move].split()[1:]
            resp = MockResponse()
            resp.move = " ".join(move)
            if self.delay and len(self.delay) > self.move:
                if not timeout or timeout > self.delay[self.move]:
                    self.curtime += self.delay[self.move]
                else:
                    sleep_time = timeout + 0.00001
                    # account for time slept
                    self.delay[self.move] -= sleep_time
                    self.curtime += sleep_time
                    # try the same move next time we're asked
                    self.move -= 1
                    raise socket.timeout()
        return resp


class MockTime:
    def __init__(self, eng):
        self.eng = eng

    def time(self):
        return self.eng._time()


class MockLog:
    def __init__(self):
        self.reset()

    def reset(self):
        self.info_logs = []
        self.warn_logs = []

    def info(self, format_str, *args):
        self.info_logs.append(format_str % args)

    def warn(self, format_str, *args):
        self.warn_logs.append(format_str % args)


class GameTest(unittest.TestCase):
    def test_contruction(self):
        p = MockEngine()
        game = Game(p, p)
        self.assertEqual(game.movenumber, 1)
        self.assertEqual(game.insetup, True)
        tc = TimeControl("30s/60s")
        game = Game(p, p, tc)
        self.assertEqual(game.timecontrol, tc)
        pos = Position(Color.GOLD, 4, BASIC_SETUP)
        game = Game(p, p, tc, pos)
        self.assertEqual(game.position, pos)
        self.assertEqual(game.insetup, False)
        real_log = pyrimaa.game.log
        mock_log = MockLog()
        pyrimaa.game.log = mock_log
        try:
            info = MockResponse("info")
            info.message = "Test info message."
            pl = MockEngine(isready=[info])
            game = Game(pl, p)
            self.assertEqual(game.movenumber, 1)
            self.assertEqual(game.insetup, True)
            self.assertEqual(len(mock_log.info_logs), 1)
            self.assertEqual(len(mock_log.warn_logs), 0)
            self.assertIn(info.message, mock_log.info_logs[0])
            mock_log.reset()
            log = MockResponse("log")
            log.message = "Test log message."
            pl = MockEngine(isready=[log])
            game = Game(pl, p)
            self.assertEqual(game.movenumber, 1)
            self.assertEqual(game.insetup, True)
            self.assertEqual(len(mock_log.info_logs), 1)
            self.assertEqual(len(mock_log.warn_logs), 0)
            self.assertIn(log.message, mock_log.info_logs[0])
            mock_log.reset()
            invalid = MockResponse("bestmove")
            invalid.move = " "
            pl = MockEngine(isready=[invalid])
            game = Game(pl, p)
            self.assertEqual(game.movenumber, 1)
            self.assertEqual(game.insetup, True)
            self.assertEqual(len(mock_log.info_logs), 0)
            self.assertEqual(len(mock_log.warn_logs), 1)
            mock_log.reset()
        finally:
            pyrimaa.game.log = real_log

    def test_play(self):
        # check basic endings, goal, immobilization and elimination
        p = MockEngine()
        game = Game(p, p)
        self.assertEqual(game.play(), (0, 'g'))
        for num, move in enumerate(game.moves):
            self.assertEqual(move, goal_moves[num])
        self.assertEqual(game.result, (0, 'g'))
        self.assertRaises(RuntimeError, game.play)
        p = MockEngine(moves=immo_moves)
        game = Game(p, p)
        self.assertEqual(game.play(), (1, 'm'))
        p = MockEngine(moves=elim_moves)
        game = Game(p, p)
        self.assertEqual(game.play(), (1, 'e'))
        # check bot resign ending
        p = MockEngine(moves=resign_moves)
        game = Game(p, p)
        self.assertEqual(game.play(), (0, 'r'))
        # check illegality of taking opponent steps
        p = MockEngine(moves=extra_step_moves)
        game = Game(p, p)
        self.assertEqual(game.play(), (1, 'i'))
        self.assertEqual(p.move, 4)
        # check illegality of 3 time repetition
        p = MockEngine(moves=repetition_moves)
        game = Game(p, p)
        self.assertEqual(game.play(), (0, 'i'))
        self.assertEqual(p.move, 7)
        # check illegality of not changing the board state
        p = MockEngine(moves=null_moves)
        game = Game(p, p)
        self.assertEqual(game.play(), (1, 'i'))
        self.assertEqual(p.move, 4)
        # check loose setup enforcement
        p = MockEngine(moves=handicap_moves)
        game = Game(p, p)
        self.assertEqual(game.play(), (1, 'i'))
        game = Game(p, p, strict_setup=False)
        self.assertEqual(game.play(), (1, 'e'))

    def test_mintimeleft_handling(self):
        rt = pyrimaa.game.time
        # check sending stop to bot with low time left
        tc = TimeControl("3s/0s/0")
        p = MockEngine(delay=[0, 1.1, 3.1])
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, tc, min_timeleft=1.1)
        self.assertEqual(game.play(), (1, 't'))
        self.assertEqual(p.stopCount, 1)
        self.assertEqual(p.stopMove, 1)
        tc = TimeControl("3s/0s/0")
        p = MockEngine(delay=[2, 2, 0])
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, tc, min_timeleft=1.5)
        self.assertEqual(game.play(), (0, 'g'))
        self.assertEqual(p.stopCount, 2)
        self.assertEqual(p.stopMove, 0)
        pyrimaa.game.time = rt

    def test_timecontrol_handling(self):
        rt = pyrimaa.game.time
        # check timecontrol enforcement
        tc = TimeControl("1s/0s/0")
        p = MockEngine(delay=[0, 0, 1.1])
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, tc)
        self.assertEqual(game.play(), (1, 't'))
        self.assertEqual(p.stopCount, 1)
        # check reserve is correctly added when not 100%
        tc = TimeControl("1s/0s/50")
        p = MockEngine(delay=[0, 0, 0, 0, 1.6])
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, tc)
        self.assertEqual(game.play(), (1, 't'))
        self.assertEqual(p.stopCount, 1)
        p = MockEngine(delay=[0, 0, 0, 0, 1.2])
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, tc)
        self.assertEqual(game.play(), (0, 'g'))
        self.assertEqual(p.stopCount, 0)
        # additionally check that the correct options were sent to the bot
        expected_options_set = {'tctotal': [0, 0], 'tcmove': [1, 1],
                'tcturns': [0, 0], 'tcreserve': [0, 0], 'tcmax': [0, 0],
                'tcpercent': [50, 50], 'tcturntime': [0, 0],
                'moveused': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0],
                'sreserve': [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3,
                    3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7, 8,
                    8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11, 11, 11, 12,
                    12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 15, 15, 15, 15,
                    16, 16, 16, 16, 17, 17, 17, 17, 18, 18, 18, 18, 19, 19, 19,
                    19, 20, 20, 20],
                'greserve': [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2,
                    3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7,
                    8, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11, 11, 11, 12,
                    12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 15, 15, 15, 15,
                    16, 16, 16, 16, 17, 17, 17, 17, 18, 18, 18, 18, 19, 19, 19,
                    19],
                }
        for option, value in expected_options_set.items():
            self.assertIn(option, p.options_set)
            self.assertEqual(p.options_set[option], value)
        # check protocol version 0 also gets the correct options
        tc = TimeControl("1s/0s/50")
        p = MockEngine(delay=[0, 0, 0, 0, 1.2])
        p.protocol_version = 0
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, tc)
        self.assertEqual(game.play(), (0, 'g'))
        self.assertEqual(p.stopCount, 0)
        # additionally check that the correct options were sent to the bot
        expected_options_set = {'tctotal': [0, 0], 'tcmove': [1, 1],
                'tcturns': [0, 0], 'tcreserve': [0, 0], 'tcmax': [0, 0],
                'tcpercent': [50, 50], 'tcturntime': [0, 0],
                'moveused': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0],
                'breserve': [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3,
                    3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7, 8,
                    8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11, 11, 11, 12,
                    12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 15, 15, 15, 15,
                    16, 16, 16, 16, 17, 17, 17, 17, 18, 18, 18, 18, 19, 19, 19,
                    19, 20, 20, 20],
                'wreserve': [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2,
                    3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7,
                    8, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11, 11, 11, 12,
                    12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 15, 15, 15, 15,
                    16, 16, 16, 16, 17, 17, 17, 17, 18, 18, 18, 18, 19, 19, 19,
                    19],
                }
        for option, value in expected_options_set.items():
            self.assertIn(option, p.options_set)
            self.assertEqual(p.options_set[option], value)
        # check reserve is correctly deducted when reserve addition is not 100%
        tc = TimeControl("1s/1s/50")
        p = MockEngine(delay=[0, 0, 1.5, 0, 1.6])
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, tc)
        self.assertEqual(game.play(), (1, 't'))
        self.assertEqual(p.stopCount, 1)
        # check maximum reserve
        tc = TimeControl("1s/1s/100/1s")
        p = MockEngine(delay=[0, 0, 0, 0, 0, 0, 0, 2.1])
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, tc)
        self.assertEqual(game.play(), (0, 't'))
        self.assertEqual(p.stopCount, 1)
        # check game time limit
        tc = TimeControl("1s/1s/100/0/2s")
        p = MockEngine(delay=[0, 0, 1, 1, 0.1])
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, tc)
        self.assertEqual(game.play(), (1, 's'))
        self.assertEqual(p.stopCount, 1)
        # check game move limit
        tc = TimeControl("1s/1s/100/0/33t")
        p = MockEngine()
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, tc)
        self.assertEqual(game.play(), (0, 's'))
        self.assertEqual(p.stopCount, 0)
        # check maximum move time limit
        tc = TimeControl("1s/1s/100/0/0/2s")
        p = MockEngine(delay=[0, 0, 0, 0, 2.1])
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, tc)
        self.assertEqual(game.play(), (1, 't'))
        self.assertEqual(p.stopCount, 1)
        # check differing time control for each player
        tc = TimeControl("1s/1s/100/1s")
        p = MockEngine(delay=[0, 0, 0, 0, 2.1, 2.1])
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, [None, tc])
        self.assertEqual(game.play(), (0, 't'))
        self.assertEqual(p.stopCount, 1)
        tc1 = TimeControl("2s/0s/100")
        tc2 = TimeControl("1s/4s/100/6s")
        p = MockEngine(delay=[0, 0, 0, 0, 0, 5, 0, 0, 7.5])
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, [tc1, tc2])
        self.assertEqual(game.play(), (0, 'g'))
        self.assertEqual(p.stopCount, 0)
        p = MockEngine(delay=[0, 0, 0, 0, 5])
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, [tc1, tc2])
        self.assertEqual(game.play(), (1, 't'))
        self.assertEqual(p.stopCount, 1)
        p = MockEngine(delay=[0, 0, 0, 0, 0, 0, 0, 0, 0, 7.5])
        pyrimaa.game.time = MockTime(p)
        game = Game(p, p, [tc1, tc2])
        self.assertEqual(game.play(), (0, 't'))
        self.assertEqual(p.stopCount, 1)
        pyrimaa.game.time = rt
