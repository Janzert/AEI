# Copyright (c) 2008 Brian Haskin Jr.
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
# THE SOFTWARE.

import math
import socket
import time

import board

from aei import StdioEngine, SocketEngine, EngineController, EngineException

SRV_HOST = "127.0.0.1"
SRV_PORT = 40007

def playgame(engines, position=None, waittime=300, movetime=0, reserve=None):
    if position is None:
        position = board.Position(board.COL_GOLD, 4, board.BLANK_BOARD)
    if reserve:
        for eng in engines:
            eng.reserve = reserve
    ply = 1
    while ((ply < 3 or not position.is_end_state())
            and ply < 300):
        eng = engines[(ply-1) % 2]

        if reserve:
            eng.setoption("tcmoveused", 0)
            eng.setoption("wreserve", engines[0].reserve)
            eng.setoption("breserve", engines[1].reserve)
        eng.go()
        starttime = time.time()
        endtime = starttime + waittime
        resp = None
        try:
            while time.time() < endtime:
                wait = endtime - time.time()
                resp = eng.get_response(wait)
                if resp.type == "bestmove":
                    break
        except socket.timeout:
            for engine in engines:
                engine.stop()
                engine.isready(300)
            break

        if resp and resp.type == "bestmove":
            if reserve:
                movelength = time.time()-starttime
                moveexcess = movelength - movetime
                eng.reserve = max(min(int(eng.reserve - moveexcess), reserve), -1)
                if eng.reserve < 0:
                    print "Engine", eng.ident['name'], "would have timed out."
            steps = board.parse_move(resp.move)
            position = position.do_move(steps)
            for engine in engines:
                engine.makemove(resp.move)
        else:
            print "No move received from %s" % (eng.ident["name"])
            break
        ply += 1

    if resp and hasattr(resp, "move"):
        print resp.move
    print position.to_long_str()

    return (position.is_end_state(), position)

engines = []

permove = 2
max_reserve = 30

eng = EngineController(StdioEngine("../D/bot_opfor"))
print "Bot 1: %s Author: %s" % (eng.ident['name'], eng.ident['author'])
if max_reserve:
    eng.setoption("tcmove", permove)
    eng.setoption("tcmax", max_reserve)
else:
    eng.setoption("depth", 8)
eng.setoption("hash", 100)
eng.setoption("opening_book", 1)
eng.ident['name'] += " cur"
engines.append(eng)

eng = EngineController(SocketEngine("../bot_opfor2008cc", legacy_mode=True))
print "Bot 2: %s Author: %s" % (eng.ident['name'], eng.ident['author'])
if max_reserve:
    eng.setoption("tcmove", permove)
    eng.setoption("tcmax", max_reserve)
else:
    eng.setoption("depth", 8)
eng.setoption("hash", 100)
eng.setoption("opening_book", 1)
eng.ident['name'] += " cc"
engines.append(eng)

gold_score = 0
silver_score = 0
tie_score = 0
matchlength = 1000
maxrepeats = 0
total_repeats = 0
endings = dict()
try:
    for i in range(matchlength):
        for eng in engines:
            eng.newgame()
            eng.isready(30)

        (result, endposition) = playgame(engines, waittime=600, movetime=permove, reserve=max_reserve)
        if result == 1:
            gold_score += 1
            engines[0].gold_score += 1
        elif result == -1:
            silver_score += 1
            engines[1].silver_score += 1
        else:
            tie_score += 1
        for eng in engines:
            print "%s: %d %d %d" % (eng.ident['name'], eng.gold_score+eng.silver_score, eng.gold_score, eng.silver_score)
        print "Gold score: %d Silver score: %d" % (gold_score, silver_score)
        endings[endposition] = endings.get(endposition, 0) +1
        if endings[endposition] > 1:
            print "Game repeated %d times" % (endings[endposition]-1)
            total_repeats += 1
        if endings[endposition]-1 > maxrepeats:
            maxrepeats = endings[endposition]-1
        if maxrepeats > 0:
            print "Maximum repeats %d, total %d" % (maxrepeats, total_repeats)
        if tie_score > 0:
            print "%d inconclusive games" % tie_score
        eng = engines.pop()
        engines.insert(0, eng)
except socket.timeout:
    print "Engine timed out"

for eng in engines:
    eng.quit()

