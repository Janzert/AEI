#! /usr/bin/python

# Copyright (c) 2009 Brian Haskin Jr.
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

import logging
import re
import socket
import sys
import time

from ConfigParser import SafeConfigParser, NoOptionError

from pyrimaa.aei import EngineController, StdioEngine, SocketEngine
from pyrimaa import board
from pyrimaa.board import Color, Position

logging.basicConfig(level=logging.WARN)
log = logging.getLogger("roundrobin")

def parse_timefield(full_field, start_unit="m"):
    unit_order = " smhd"
    units = {"s": 1, "m": 60, "h": 60*60, "d": 60*60*24}
    num_re = re.compile("[0-9]+")
    units[":"] = units[start_unit]
    seconds = 0
    field = full_field
    nmatch = num_re.match(field)
    while nmatch:
        end = nmatch.end()
        num = int(field[:end])
        if len(field) == end or field[end] == ":":
            sep = start_unit
            start_unit = unit_order[unit_order.find(start_unit)-1]
        else:
            sep = field[end]
        if sep not in units:
            raise ValueError("Invalid time unit encountered %s" % (sep))
        seconds += num * units[sep]
        if ":" in units:
            del units[":"]
        field = field[end+1:]
        nmatch = num_re.match(field)
    if field:
        raise ValueError("Invalid time field encountered %s" % (full_field))
    return seconds

def parse_timecontrol(tc_str):
    field_re = re.compile("[^/]*")
    def split_tc(tstr):
        fmatch = field_re.match(tc_str)
        if not fmatch:
            f_str = tstr
            rest = ""
        else:
            end = fmatch.end()
            f_str = tstr[:end]
            rest = tstr[end + 1:]
        return (f_str, rest)
    tc = {}
    f_str, tc_str = split_tc(tc_str)
    tc['move'] = parse_timefield(f_str)
    f_str, tc_str = split_tc(tc_str)
    tc['reserve'] = parse_timefield(f_str)
    f_str, tc_str = split_tc(tc_str)
    if f_str:
        tc['percent'] = int(f_str)
    else:
        tc['percent'] = 100
    f_str, tc_str = split_tc(tc_str)
    tc['max'] = parse_timefield(f_str)
    f_str, tc_str = split_tc(tc_str)
    try:
        tc['turns'] = int(f_str)
        tc['total'] = 0
    except ValueError:
        tc['turns'] = 0
        tc['total'] = parse_timefield(f_str, "h")
    tc['turntime'] = parse_timefield(tc_str)
    return tc

def playgame(gold_eng, silver_eng, timecontrol=None, position=None):
    engines = (gold_eng, silver_eng)
    if timecontrol:
        time_incr = timecontrol['move']
        reserves = [0, 0]
        reserves[0] = reserves[1] = timecontrol['reserve']
        reserve_per = timecontrol['percent'] / 100.0
        reserve_max = timecontrol['max']
        max_moves = timecontrol['turns']
        max_gametime = timecontrol['total']
        max_turn = timecontrol['turntime']
        for eng in engines:
            eng.setoption("tcmove", time_incr)
            eng.setoption("tcreserve", timecontrol['reserve'])
            eng.setoption("tcpercent", timecontrol['percent'])
            eng.setoption("tcmax", reserve_max)
            eng.setoption("tcturns", max_moves)
            eng.setoption("tctotal", max_gametime)
            eng.setoption("tcturntime", max_turn)
    for eng in engines:
        eng.newgame()
        if position:
            eng.setposition(position)
        eng.isready()
    insetup = False
    if not position:
        insetup = True
        position = Position(Color.GOLD, 4, board.BLANK_BOARD)
    starttime = time.time()
    while insetup or not position.is_end_state():
        #print "gs"[position.color]
        #print position.board_to_str()
        side = position.color
        engine = engines[side]
        if timecontrol:
            engine.setoption("greserve", int(reserves[0]))
            engine.setoption("sreserve", int(reserves[1]))
            movestart = time.time()
            engine.setoption("moveused", 0)
        engine.go()
        if timecontrol:
            timeout = movestart + time_incr + reserves[side]
            if max_turn and starttime + max_turn > timeout:
                timeout = starttime + max_turn
        else:
            timeout = None
        try:
            while time.time() < timeout:
                if timeout:
                    wait = timeout - time.time()
                else:
                    wait = None
                resp = engine.get_response(wait)
                if resp.type == "bestmove":
                    break
                if resp.type == "info":
                    log.info("%s info: %s" % ("gs"[side], resp.message))
                elif resp.type == "log":
                    log.info("%s log: %s" % ("gs"[side], resp.message))
        except socket.timeout:
            engine.stop()

        if resp and resp.type == "bestmove":
            if timecontrol:
                moveend = time.time()
                if moveend > timeout:
                    return (side^1, "t", position)
                if not insetup:
                    reserve_incr = ((time_incr - (moveend - movestart))
                            * reserve_per)
                    reserves[side] += reserve_incr
                    reserves[side] = min(reserves[side], reserve_max)
            move = resp.move
            position = position.do_move_str(move)
            log.info("position:\n%s", position.board_to_str())
            for eng in engines:
                eng.makemove(move)
            if insetup and side == Color.SILVER:
                insetup = False
        else:
            return (side^1, "t", position)

    if position.is_goal():
        result = (min(position.is_goal(), 0), "g", position)
    elif position.is_rabbit_loss():
        result = (min(position.is_rabbit_loss(), 0), "e", position)
    else: # immobilization
        assert len(position.get_steps()) == 0
        result = (position.color^1, "m", position)
    return result

def run_bot(bot, config, global_options):
    cmdline = config.get(bot['name'], "cmdline")
    if config.has_option(bot['name'], "communication_method"):
        com_method = config.get(bot['name'],
                "communication_method").lower()
    else:
        com_method = "stdio"
    if com_method == "stdio":
        engine = StdioEngine(cmdline, log=log)
    elif com_method == "socket":
        engine = SocketEngine(cmdline, log=log)
    engine = EngineController(engine)
    for option, value in global_options:
        engine.setoption(option, value)
    for name, value in config.items(bot['name']):
        if name.startswith("bot_"):
            engine.setoption(name[4:], value)
    return engine

def main():
    config = SafeConfigParser()
    if not config.read("roundrobin.cfg"):
        print "Could not read 'roundrobin.cfg'."
        return 1
    bot_configs = set(config.sections())
    if "global" not in bot_configs:
        print "Did not find expected 'global' section in configuration file."
        return 1
    bot_configs.remove('global')

    rounds = config.getint("global", "rounds")
    print "Number of rounds: ", rounds
    try:
        tctl_str = config.get("global", "timecontrol")
        timecontrol = parse_timecontrol(tctl_str)
        print "At timecontrol %s" % (tctl_str,)
    except NoOptionError:
        timecontrol = None

    if config.has_option("global", "loglevel"):
        levelstr = config.get("global", "loglevel").lower()
        levels = {"info": logging.INFO, "debug": logging.DEBUG,
                "warn": logging.WARN, "error": logging.ERROR}
        level = levels.get(levelstr, None)
        if level:
            log.setLevel(level)
        else:
            print "Attempted to set unrecognized log level"
            return 1

    global_options = []
    for name, value in config.items("global"):
        if name.startswith("bot_"):
            global_options.append((name[4:], value))
    if global_options:
        print "Giving these settings to all bots:"
        for name, value in global_options:
            print "%s: %s" % (name, value)

    bots = []
    for bname in config.get("global", "bots").split():
        for bsection in bot_configs:
            if bname.lower() == bsection.lower():
                bot_options = []
                for name, value in config.items(bsection):
                    if name.startswith("bot_"):
                        bot_options.append((name[4:], value))
                bot = {'name': bsection, 'options': bot_options, 'gold': 0,
                        'wins': 0, 'timeouts': 0, 'reasons': dict()}
                bots.append(bot)
                break
        else:
            print "Did not find a bot section for %s" % (bname)
            return 1

    for round_num in xrange(rounds):
        for bot_ix, bot in enumerate(bots[:-1]):
            for opp in bots[bot_ix+1:]:
                if bot['gold'] <= opp['gold']:
                    gbot = bot
                    sbot = opp
                else:
                    gbot = opp
                    sbot = bot
                gbot['gold'] += 1
                gengine = run_bot(gbot, config, global_options)
                sengine = run_bot(sbot, config, global_options)
                wside, reason, position = playgame(gengine, sengine,
                        timecontrol)
                winner = [gbot, sbot][wside]
                print "gs"[position.color]
                print position.board_to_str()
                print "%s wins because of %s playing side %s" % (
                        winner['name'], reason, "gs"[wside])
                winner['wins'] += 1
                if reason == 't':
                    [gbot, sbot][wside ^ 1]['timeouts'] += 1
                winner['reasons'][reason] = winner['reasons'].get(reason, 0) + 1
                gengine.quit()
                sengine.quit()
                time.sleep(5)
                gengine.cleanup()
                sengine.cleanup()
        print "After round %d:" % (round_num+1,)
        for bot in bots:
            print "%s has %d wins and %d timeouts" % (bot['name'], bot['wins'],
                    bot['timeouts'])
            for name, value in bot['reasons'].items():
                print "    %d by %s" % (value, name)

    return 0

if __name__ == "__main__":
    sys.exit(main())

