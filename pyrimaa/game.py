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

import logging
import time
import socket
from collections import defaultdict

from pyrimaa.board import BLANK_BOARD, Color, IllegalMove, Position

log = logging.getLogger("game")

class Game(object):
    def __init__(self, gold, silver, timecontrol=None, start_position=None,
            strict_setup=True, min_timeleft=None):
        self.engines = (gold, silver)
        try:
            self.timecontrol = timecontrol[0]
            self.side_tc = timecontrol
        except TypeError:
            self.timecontrol = timecontrol
            self.side_tc = [timecontrol, timecontrol]
        self.reserves = [None, None]
        if timecontrol:
            for side, eng in enumerate(self.engines):
                if not self.side_tc[side]:
                    continue
                self.reserves[side] = self.side_tc[side].reserve
                eng.setoption("tcmove", self.side_tc[side].move)
                eng.setoption("tcreserve", self.side_tc[side].reserve)
                eng.setoption("tcpercent", self.side_tc[side].percent)
                eng.setoption("tcmax", self.side_tc[side].max_reserve)
                eng.setoption("tcturns", self.side_tc[side].turn_limit)
                eng.setoption("tctotal", self.side_tc[side].time_limit)
                eng.setoption("tcturntime", self.side_tc[side].max_turntime)
        for eng in self.engines:
            eng.newgame()
            if start_position:
                eng.setposition(start_position)
            eng.isready()
        self.insetup = False
        self.position = start_position
        if not start_position:
            self.insetup = True
            self.position = Position(Color.GOLD, 4, BLANK_BOARD)
        self.strict_setup = strict_setup
        self.min_timeleft = min_timeleft
        self.movenumber = 1
        self.limit_winner = 1
        self.moves = []
        self.repetition_count = defaultdict(int)
        self.result = None

    def play(self):
        if self.result:
            raise RuntimeError("Tried to play a game that was already played.")
        position = self.position
        starttime = time.time()
        while not position.is_end_state() or self.insetup:
            side = position.color
            engine = self.engines[side]
            tc = self.side_tc[side]
            if tc:
                if tc.time_limit:
                    endtime_limit = starttime + tc.time_limit
                if engine.protocol_version == 0:
                    if self.reserves[0] is not None:
                        engine.setoption("wreserve", int(self.reserves[0]))
                    if self.reserves[1] is not None:
                        engine.setoption("breserve", int(self.reserves[1]))
                    engine.setoption("tcmoveused", 0)
                if self.reserves[0] is not None:
                    engine.setoption("greserve", int(self.reserves[0]))
                if self.reserves[1] is not None:
                    engine.setoption("sreserve", int(self.reserves[1]))
                engine.setoption("moveused", 0)
            movestart = time.time()
            engine.go()
            if tc:
                timeout = movestart + tc.move + self.reserves[side]
                if tc.max_turntime and movestart + tc.max_turntime < timeout:
                    timeout = movestart + tc.max_turntime
                if tc.time_limit and endtime_limit < timeout:
                    timeout = endtime_limit
            else:
                timeout = None
            waittime = None
            resp = None
            stopsent = False
            stoptime = None
            if timeout and self.min_timeleft:
                stoptime = timeout - self.min_timeleft
            while True:
                now = time.time()
                if stoptime and not stopsent and now >= stoptime:
                    # try and get a move before time runs out
                    engine.stop()
                    log.info("Engine sent stop command to prevent timeout")
                    stopsent = True
                if timeout and now > timeout:
                    if not stopsent:
                        engine.stop()
                    break
                if timeout:
                    waittime = timeout - now
                    if stoptime and not stopsent and now + waittime > stoptime:
                        waittime = max(0, (stoptime - now) + 0.2)
                try:
                    resp = engine.get_response(waittime)
                    if resp.type == "bestmove":
                        break
                    if resp.type == "info":
                        log.info("%s info: %s" % ("gs"[side], resp.message))
                    elif resp.type == "log":
                        log.info("%s log: %s" % ("gs"[side], resp.message))
                except socket.timeout:
                    pass
            moveend = time.time()

            if tc and moveend > timeout:
                if tc.time_limit and endtime_limit < moveend:
                    self.result = (self.limit_winner, "s")
                else:
                    self.result = (side^1, "t")
                return self.result
            if not resp or resp.type != "bestmove":
                raise RuntimeError(
                        "Stopped waiting without a timeout or a move")
            if tc:
                if not self.insetup:
                    reserve_change = tc.move - (moveend - movestart)
                    if reserve_change > 0:
                        # if we are adding to the reserve only apply the
                        # percentage specified by the time control
                        reserve_change *= tc.percent / 100.0
                    self.reserves[side] += reserve_change
                    if tc.max_reserve:
                        self.reserves[side] = min(self.reserves[side],
                                tc.max_reserve)
            move = resp.move
            if move.lower() == "resign":
              self.result = (side^1, "r")
              return self.result
            self.moves.append("%d%s %s" % (self.movenumber,
                "gs"[position.color], move))
            if self.insetup:
                position = position.do_move_str(move,
                        strict_checks=self.strict_setup)
            else:
                position = position.do_move_str(move)
            self.repetition_count[position] += 1
            if self.repetition_count[position] > 2:
                raise IllegalMove("Tried move resulting in a 3rd time repetition")
            self.position = position
            if position.color == Color.GOLD:
                self.movenumber += 1
            log.info("position:\n%s", position.board_to_str())
            for eng in self.engines:
                eng.makemove(move)
            if self.insetup and side == Color.SILVER:
                self.insetup = False
            if not self.insetup:
                bstr = position.board_to_str("short")
                gp = 0
                for p in "EMHDCR":
                    gp += bstr.count(p)
                sp = 0
                for p in "emhdcr":
                    sp += bstr.count(p)
                if gp > sp:
                    limit_winner = 0
                elif sp > gp:
                    limit_winner = 1
            if tc and tc.turn_limit and self.movenumber > tc.turn_limit:
                self.result = (limit_winner, "s")
                return self.result

        if position.is_goal():
            result = (0-min(position.is_goal(), 0), "g")
        elif position.is_rabbit_loss():
            result = (0-min(position.is_rabbit_loss(), 0), "e")
        else: # immobilization
            assert len(position.get_steps()) == 0
            result = (position.color^1, "m")
        self.result = result
        return result

