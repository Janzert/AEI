#!/usr/bin/env python

# Copyright (c) 2009-2015 Brian Haskin Jr.
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

from __future__ import print_function

import logging
import re
import socket
import sys
import time

from argparse import ArgumentParser
try:
    from ConfigParser import SafeConfigParser, NoOptionError
    ConfigParser = SafeConfigParser
except ModuleNotFoundError:
    from configparser import ConfigParser, NoOptionError
    xrange = range

from pyrimaa import aei
from pyrimaa.game import Game
from pyrimaa.util import TimeControl

log = logging.getLogger("roundrobin")


def run_bot(bot, config, global_options):
    cmdline = config.get(bot['name'], "cmdline")
    if config.has_option(bot['name'], "communication_method"):
        com_method = config.get(bot['name'], "communication_method").lower()
    else:
        com_method = "stdio"
    eng_com = aei.get_engine(com_method, cmdline, "roundrobin.aei")
    engine = aei.EngineController(eng_com)
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


def get_config(args=None):
    class NotSet:
        pass

    notset = NotSet()
    parser = ArgumentParser(
        description="Play engines in a round robin tournament.")
    parser.add_argument("--config",
                        default="roundrobin.cfg",
                        help="Configuration file to use")
    parser.add_argument("--log", help="Set log output level")
    parser.add_argument("--pgn", help="PGN results filename")
    parser.add_argument("-r", "--rounds",
                        type=int,
                        help="Number of rounds to run")
    parser.add_argument(
        "--stop-time",
        type=int,
        help="Number of seconds to leave when sending a bot a stop command")
    parser.add_argument(
        "--strict-setup",
        action="store_true",
        default=notset,
        help="Require the setup moves to be complete and legal")
    parser.add_argument(
        "--allow-setup",
        dest="strict_setup",
        action="store_false",
        help="Allow incomplete or otherwise illegal setup moves")
    parser.add_argument("--timecontrol", "--tc", help="Timecontrol to use")
    parser.add_argument("bots", nargs="*", help="Bots to use in tournament")
    args = parser.parse_args(args)

    config = ConfigParser()
    if config.read(args.config) != [args.config]:
        print("Could not open '%s'" % (args.config, ))
        return 1
    args.ini = config
    args.bot_sections = set(config.sections())
    if "global" not in args.bot_sections:
        print("Did not find expected 'global' section in configuration file.")
        return 1
    args.bot_sections.remove('global')

    try:
        loglevel = config.get("global", "loglevel")
    except NoOptionError:
        loglevel = None
    loglevel = loglevel if args.log is None else args.log
    if loglevel is not None:
        loglevel = logging.getLevelName(loglevel)
        if not isinstance(loglevel, int):
            print("Bad log level %s, use ERROR, WARNING, INFO or DEBUG." % (
                loglevel,
            ))
        logging.basicConfig(level=loglevel)

    if args.pgn is None:
        try:
            args.pgn = config.get("global", "pgn_filename")
        except:
            pass

    if args.rounds is None:
        try:
            args.rounds = config.getint("global", "rounds")
        except NoOptionError:
            pass
    if args.timecontrol is None:
        try:
            args.timecontrol = config.get("global", "timecontrol")
        except NoOptionError:
            pass

    if args.strict_setup is notset:
        try:
            args.strict_setup = config.getboolean("global", "strict_setup")
        except NoOptionError:
            args.strict_setup = None

    if args.stop_time is None:
        try:
            args.stop_time = config.getint("global", "stop_time")
        except NoOptionError:
            pass

    if len(args.bots) == 0:
        try:
            args.bots = config.get("global", "bots").split()
        except NoOptionError:
            args.bots = args.bot_sections

    args.global_options = list()
    for option, value in config.items("global"):
        if option.startswith("bot_"):
            args.global_options.append((option[4:], value))

    return args


def main(args=None):
    cfg = get_config(args)
    if cfg.rounds:
        print("Number of rounds: %d" % (cfg.rounds, ))
    else:
        print("Number of rounds not specified, running 1 round.")
        cfg.rounds = 1

    try:
        tctl_str = cfg.timecontrol
        if tctl_str.lower() == "none":
            timecontrol = None
        else:
            timecontrol = TimeControl(tctl_str)
            print("At timecontrol %s" % (tctl_str, ))
    except NoOptionError:
        timecontrol = None

    if cfg.global_options:
        print("Giving these settings to all bots:")
        for name, value in cfg.global_options:
            print("  %s: %s" % (name, value))

    print("Playing bots: ", end='')
    for bot in cfg.bots:
        print(bot, end=' ')
    print()

    # setup to write a bayeselo compatible pgn file
    write_pgn = False
    if cfg.pgn is not None:
        try:
            pgn_file = open(cfg.pgn, "a+")
        except IOError:
            print("Could not open pgn file %s" % (cfg.pgn, ))
            return 1
        print("Writing results to pgn file: %s" % (cfg.pgn, ))
        write_pgn = True

    bots = []
    for bname in cfg.bots:
        for bsection in cfg.bot_sections:
            if bname.lower() == bsection.lower():
                bot_options = []
                for name, value in cfg.ini.items(bsection):
                    if name.startswith("bot_"):
                        bot_options.append((name[4:], value))
                bot = {
                    'name': bsection,
                    'options': bot_options,
                    'gold': 0,
                    'wins': 0,
                    'timeouts': 0,
                    'reasons': dict()
                }
                if cfg.ini.has_option(bsection, "timecontrol"):
                    tctl_str = cfg.ini.get(bsection, "timecontrol")
                    if tctl_str.lower() == "none":
                        tc = None
                    else:
                        tc = TimeControl(tctl_str)
                        print("bot %s at timecontrol %s" % (bsection, tctl_str))
                    bot['timecontrol'] = tc
                bots.append(bot)
                break
        else:
            print("Did not find a bot section for %s" % (bname))
            return 1

    start_time = time.time()
    for round_num in xrange(cfg.rounds):
        for bot_ix, bot in enumerate(bots[:-1]):
            for opp in bots[bot_ix + 1:]:
                if bot['gold'] <= opp['gold']:
                    gbot = bot
                    sbot = opp
                else:
                    gbot = opp
                    sbot = bot
                gbot['gold'] += 1
                gengine = run_bot(gbot, cfg.ini, cfg.global_options)
                sengine = run_bot(sbot, cfg.ini, cfg.global_options)
                tc = [timecontrol, timecontrol]
                if 'timecontrol' in gbot:
                    tc[0] = gbot['timecontrol']
                if 'timecontrol' in sbot:
                    tc[1] = sbot['timecontrol']
                game = Game(gengine, sengine, tc,
                            strict_setup=cfg.strict_setup,
                            min_timeleft=cfg.stop_time)
                wside, reason = game.play()
                gengine.quit()
                sengine.quit()
                winner = [gbot, sbot][wside]
                loser = [gbot, sbot][wside ^ 1]

                # Display result of game
                print("%d%s" % (game.movenumber, "gs" [game.position.color]))
                print(game.position.board_to_str())
                print("%s beat %s because of %s playing side %s" % (
                    winner['name'], loser['name'], reason, "gs" [wside]
                ))

                # Record game result stats
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
                    pgn_file.write('[White "%s"]\n' % (gbot['name'], ))
                    pgn_file.write('[Black "%s"]\n' % (sbot['name'], ))
                    if timecontrol:
                        pgn_file.write('[TimeControl "%s"]\n' % (tctl_str, ))
                    pgn_file.write('[PlyCount "%s"]\n' % (ply_count, ))
                    pgn_file.write('[ResultCode "%s"]\n' % (reason, ))
                    pgn_file.write('[Result "%s"]\n' % (results[wside], ))
                    pgn_file.write('\n')
                    for move in game.moves:
                        pgn_file.write('%s\n' % (move, ))
                    pgn_file.write('%s\n\n' % (results[wside]))
                    pgn_file.flush()

                # give the engines up to 30 more seconds to exit normally
                for i in range(30):
                    if (not gengine.is_running() and not sengine.is_running()):
                        break
                    time.sleep(1)
                gengine.cleanup()
                sengine.cleanup()
        round_end = time.time()
        total_time = round_end - start_time
        print("After round %d and %s:" % (round_num + 1,
                                          format_time(total_time)))
        for bot in bots:
            print("%s has %d wins and %d timeouts" % (bot['name'], bot['wins'],
                                                      bot['timeouts']))
            for name, value in list(bot['reasons'].items()):
                print("    %d by %s" % (value, name))

    return 0

if __name__ == "__main__":
    sys.exit(main())
