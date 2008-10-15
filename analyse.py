#! /usr/bin/python

import socket
import sys
import time

from subprocess import Popen

import board

from aei import SocketEngine, StdioEngine, EngineController, EngineException

if len(sys.argv) < 2:
    print "usage: analyse boardfile"
    sys.exit()

pfile = open(sys.argv[1], 'r')
plines = pfile.readlines()
movenum, pos = board.parse_long_pos(plines)
pfile.close()

#eng = EngineController(SocketEngine("./bot_opfor2008cc", legacy_mode=True))
eng = EngineController(StdioEngine("../D/bot_opfor"))

#eng.setoption("tcmove", 120)
#eng.setoption("tcmax", 600)
#eng.setoption("tcmoveused", 0)
#eng.setoption("wreserve", 300)
#eng.setoption("breserve", 300)
#eng.setoption("root_lmr", 0)
#eng.setoption("use_lmr", 0)

#eng.setoption("log_console", 1)
#eng.setoption("depth", "12")
eng.setoption("hash", 500)
print pos.to_long_str()
eng.setposition(pos)
eng.go()

while True:
    try:
        resp = eng.get_response(10)
        if resp.type == "info":
            print resp.message
        elif resp.type == "log":
            print "log: %s" % resp.message
        elif resp.type == "bestmove":
            print "bestmove: %s" % resp.move
            break
    except socket.timeout:
        pass

eng.quit()
stop_waiting = time.time() + 60
while time.time() < stop_waiting:
    try:
        resp = eng.get_response(1)
        if resp.type == "info":
            print resp.message
        elif resp.type == "log":
            print "log: %s" % (resp.message)
    except socket.timeout:
        pass
    if eng.engine.proc.poll() is not None:
        break
eng.cleanup()

