#! /usr/bin/python

import logging
import socket
import sys
import time

from ConfigParser import SafeConfigParser

from pyrimaa import board

from pyrimaa.aei import SocketEngine, StdioEngine, EngineController

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("analyze")

if len(sys.argv) < 2:
    print "usage: analyze <board or movelist file> [move to analyze]"
    sys.exit()

have_board = False
pfile = open(sys.argv[1], 'r')
plines = pfile.readlines()
plines = [l.strip() for l in plines]
plines = [l for l in plines if l]
while plines and not plines[0][0].isdigit():
    del plines[0]
if not plines:
    print "File %s does not appear to be a board or move list." % (sys.argv[1],)
    sys.exit()
if len(plines) < 2 or plines[1][0] != '+':
    have_board = False
    if len(sys.argv) > 2:
        stop_move = sys.argv[2]
    else:
        stop_move = None
    move_list = []
    while plines and plines[0][0].isdigit():
        move = plines.pop(0)
        if stop_move and move.startswith(stop_move):
            break
        move_list.append(move)
else:
    movenum, pos = board.parse_long_pos(plines)
    have_board = True

pfile.close()

config = SafeConfigParser()
if config.read("analyze.cfg") != ["analyze.cfg"]:
    print "Could not open 'analyze.cfg'"
    sys.exit(1)

bot_section = config.get("global", "default_engine")
if config.has_option(bot_section, "communication_method"):
    com_method = config.get(bot_section, "communication_method").lower()
else:
    com_method = "stdio"
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

eng.newgame()
if have_board:
    eng.setposition(pos)
else:
    pos = board.Position(board.Color.GOLD, 4, board.BLANK_BOARD)
    for move in move_list:
        move = move[3:]
        pos = pos.do_move_str(move)
        eng.makemove(move)
print pos.board_to_str()

for option in config.options(bot_section):
    if option.startswith("post_pos_"):
        value = config.get(bot_section, option)
        eng.setoption(option[9:], value)

search_position = True
if config.has_option("global", "search_position"):
    sp_str = config.get("global", "search_position")
    search_position = not (sp_str.lower() in ["false", "0", "no"])
if search_position:
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
        if not search_position:
            break

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

