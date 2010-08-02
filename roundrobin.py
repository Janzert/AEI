#! /usr/bin/python

# Copyright (c) 2009-2010 Brian Haskin Jr.
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
from pyrimaa.game import Game
from pyrimaa.util import TimeControl

logging.basicConfig(level=logging.WARN)
log = logging.getLogger("roundrobin")

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
    else:
        raise ValueError("Bad communication method (%s) given for bot %s"
                % (com_method, bot['name']))
    engine = EngineController(engine)
    for option, value in global_options:
        engine.setoption(option, value)
    for name, value in config.items(bot['name']):
        if name.startswith("bot_"):
            engine.setoption(name[4:], value)
    return engine

def format_time(seconds):
    hours = int(seconds / 3600)
    seconds -= hours * 3600
    minutes = int(seconds / 60)
    seconds -= minutes * 60
    fmt_tm = []
    if hours:
        fmt_tm.append("%dh" % hours)
    if minutes or fmt_tm:
        fmt_tm.append("%dm" % minutes)
    fmt_tm.append("%ds" % seconds)
    return "".join(fmt_tm)

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
        if tctl_str.lower() == "none":
            timecontrol = None
        else:
            timecontrol = TimeControl(tctl_str)
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

    # setup to write a bayeselo compatible pgn file
    write_pgn = False
    if config.has_option("global", "write_pgn"):
        write_pgn = config.getboolean("global", "write_pgn")
        if write_pgn:
            try:
                pgn_name = config.get("global", "pgn_filename")
            except NoOptionError:
                print "Must specify pgn_filename option with write_pgn option."
                return 1
            pgn_file = open(pgn_name, "a+")

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

    start_time = time.time()
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
                game = Game(gengine, sengine, timecontrol)
                wside, reason = game.play()
                gengine.quit()
                sengine.quit()
                winner = [gbot, sbot][wside]
                print "%d%s" % (game.movenumber, "gs"[game.position.color])
                print game.position.board_to_str()
                print "%s wins because of %s playing side %s" % (
                        winner['name'], reason, "gs"[wside])
                winner['wins'] += 1
                if reason == 't':
                    [gbot, sbot][wside ^ 1]['timeouts'] += 1
                winner['reasons'][reason] = winner['reasons'].get(reason, 0) + 1

                # write game result to pgn file
                if write_pgn:
                    ply_count = game.movenumber * 2
                    if game.position.color:
                        ply_count -= 1
                    else:
                        ply_count -= 2
                    results = ['1-0', '0-1']
                    pgn_file.write('[White "%s"]\n' % (gbot['name'],))
                    pgn_file.write('[Black "%s"]\n' % (sbot['name'],))
                    pgn_file.write('[Result "%s"]\n' % (results[wside],))
                    pgn_file.write('[ResultCode "%s"]\n' % (reason,))
                    pgn_file.write('[PlyCount "%s"]\n' % (ply_count,))
                    if timecontrol:
                        pgn_file.write('[TimeControl "%s"]\n' % (tctl_str,))
                    pgn_file.write('%s\n\n' % (results[wside]))
                    pgn_file.flush()

                # give the engines up to 30 more seconds to exit normally
                for i in range(30):
                    if (not gengine.is_running()
                            and not sengine.is_running()):
                        break
                    time.sleep(1)
                gengine.cleanup()
                sengine.cleanup()
        round_end = time.time()
        total_time = round_end - start_time
        print "After round %d and %s:" % (round_num+1, format_time(total_time))
        for bot in bots:
            print "%s has %d wins and %d timeouts" % (bot['name'], bot['wins'],
                    bot['timeouts'])
            for name, value in bot['reasons'].items():
                print "    %d by %s" % (value, name)

    return 0

if __name__ == "__main__":
    sys.exit(main())

