#! /usr/bin/python

import logging
import socket
import sys
import time

from ConfigParser import SafeConfigParser
from subprocess import Popen

from pyrimaa import board

from pyrimaa.aei import SocketEngine, StdioEngine, EngineController

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("analyze")

if len(sys.argv) < 2:
    print "usage: analyze boardfile"
    sys.exit()

pfile = open(sys.argv[1], 'r')
plines = pfile.readlines()
movenum, pos = board.parse_long_pos(plines)
pfile.close()

config = SafeConfigParser()
if config.read("analyze.cfg") != ["analyze.cfg"]:
    print "Could not open 'analyze.cfg'"
    sys.exit(1)

bot_section = config.get("global", "default_engine")
com_method = config.get(bot_section, "communication_method").lower()
enginecmd = config.get(bot_section, "cmdline")

if com_method == "2008cc":
    eng_com = SocketEngine(enginecmd, legacy_mode=True, log=log)
elif com_method == "socket":
    eng_com = SocketEngine(enginecmd, log=log)
elif com_method == "stdio":
    eng_com = StdioEngine(enginecmd, log=log)
else:
    raise ValueError("Unrecognized communication method: %s" % (com_method,))
eng = EngineController(eng_com)

for option in config.options(bot_section):
    if option.startswith("bot_"):
        value = config.get(bot_section, option)
        eng.setoption(option[4:], value)

#eng = EngineController(SocketEngine("./bot_opfor2008cc", legacy_mode=True))
#eng = EngineController(StdioEngine("python simple_engine.py"))

#eng.setoption("tcmove", 120)
#eng.setoption("tcmax", 600)
#eng.setoption("tcmoveused", 0)
#eng.setoption("wreserve", 300)
#eng.setoption("breserve", 300)
#eng.setoption("root_lmr", 0)
#eng.setoption("use_lmr", 0)

#eng.setoption("log_console", 1)
#eng.setoption("depth", "12")
#eng.setoption("hash", 500)

print pos.board_to_str()
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
stop_waiting = time.time() + 20
while time.time() < stop_waiting:
    try:
        resp = eng.get_response(1)
        if resp.type == "info":
            print resp.message
        elif resp.type == "log":
            print "log: %s" % (resp.message)
    except socket.timeout:
        try:
            eng.quit()
        except IOError:
            pass
    if eng.engine.proc.poll() is not None:
        break
eng.cleanup()

