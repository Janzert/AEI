#!/usr/bin/env python
# Copyright (c) 2008-2015 Brian Haskin Jr.
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
import socket
import sys
import time

from argparse import ArgumentParser
from configparser import ConfigParser, NoOptionError

from pyrimaa import aei, board

log = logging.getLogger("analyze")


class ParseError(Exception):
    pass


def parse_start(start_lines, stop_move=None):
    start_lines = [l.strip() for l in start_lines]
    start_lines = [l for l in start_lines if l]
    while start_lines and not start_lines[0][0].isdigit():
        del start_lines[0]
    if not start_lines:
        raise ParseError("No board or moves")
    if len(start_lines) < 2 or start_lines[1][0] != '+':
        have_board = False
        start = []
        while start_lines and start_lines[0][0].isdigit():
            move = start_lines.pop(0)
            if stop_move and move.startswith(stop_move):
                break
            start.append(move)
    else:
        movenum, start = board.parse_long_pos(start_lines)
        have_board = True
    return have_board, start


def get_config(args=None):
    class NotSet:
        pass

    notset = NotSet()
    parser = ArgumentParser(description="Analyze a given position.")
    parser.add_argument("-b", "--bot",
                        help="Which engine to use in config file")
    parser.add_argument("-c", "--config",
                        default="analyze.cfg",
                        help="Configuration file to use.")
    parser.add_argument("--log", help="Set log output level.")
    parser.add_argument("--strict-checks",
                        action="store_true",
                        default=notset,
                        help="Use strict checking on move legality")
    parser.add_argument("--skip-checks",
                        action="store_false",
                        dest="strict_checks",
                        help="Skip extra legality checks for moves")
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
    parser.add_argument("position_file", help="File with board or move list")
    parser.add_argument("move_number", help="Move to analyze", nargs="?")
    args = parser.parse_args(args)

    config = ConfigParser()
    if config.read(args.config) != [args.config]:
        print("Could not open '%s'" % (args.config, ))
        sys.exit(1)
    try:
        loglevel = config.get("global", "log_level")
    except NoOptionError:
        loglevel = None
    loglevel = loglevel if args.log is None else args.log
    if loglevel is not None:
        loglevel = logging.getLevelName(loglevel)
        if not isinstance(loglevel, int):
            print("Bad log level \"%s\", use ERROR, WARNING, INFO or DEBUG." % (
                loglevel,
            ))
            sys.exit(1)
        logging.basicConfig(level=loglevel)

    if args.strict_checks is notset:
        try:
            args.strict_checks = config.getboolean("global", "strict_checks")
        except NoOptionError:
            args.strict_checks = False
    if args.strict_setup is notset:
        try:
            args.strict_setup = config.getboolean("global", "strict_setup")
        except NoOptionError:
            args.strict_setup = None
    try:
        args.search_position = config.getboolean("global", "search_position")
    except NoOptionError:
        args.search_position = True
    if args.bot is None:
        args.bot = config.get("global", "default_engine")
    cfg_sections = config.sections()
    if args.bot not in cfg_sections:
        print("Engine configuration for %s not found in config." % (args.bot, ))
        print("Available configs are:", end=' ')
        for section in cfg_sections:
            if section != "global":
                print(section, end=' ')
        print()
        sys.exit(1)

    try:
        args.com_method = config.get(args.bot, "communication_method").lower()
    except NoOptionError:
        args.com_method = "stdio"
    try:
        args.enginecmd = config.get(args.bot, "cmdline")
    except NoOptionError:
        print("No engine command line found in config file.")
        print("Add cmdline option for engine %s" % (args.bot, ))
        sys.exit(1)

    args.bot_options = list()
    for option in config.options(args.bot):
        if option.startswith("bot_"):
            value = config.get(args.bot, option)
            args.bot_options.append((option[4:], value))
    args.post_options = list()
    for option in config.options(args.bot):
        if option.startswith("post_pos_"):
            value = config.get(args.bot, option)
            args.post_options.append((option[9:], value))

    return args


def main(args=None):
    try:
        cfg = get_config(args)
    except SystemExit as exc:
        return exc.code

    with open(cfg.position_file, 'r') as pfile:
        plines = pfile.readlines()
    try:
        have_board, start = parse_start(plines, cfg.move_number)
    except ParseError:
        print("File %s does not appear to be a board or move list." % (
            cfg.position_file,
        ))
        return 0

    if cfg.strict_checks:
        print("Enabling full legality checking on moves")

    if cfg.strict_setup is not None:
        if cfg.strict_setup:
            print("Enabling full legality checking on setup")
        else:
            print("Disabling full legality checking on setup")

    eng_com = aei.get_engine(cfg.com_method, cfg.enginecmd, "analyze.aei")
    try:
        eng = aei.EngineController(eng_com)
    except aei.EngineException as exc:
        print(exc.message)
        print("Bot probably did not start. Is the command line correct?")
        eng_com.cleanup()
        return 1
    try:
        for option, value in cfg.bot_options:
            eng.setoption(option, value)

        eng.newgame()
        if have_board:
            pos = start
            eng.setposition(pos)
        else:
            pos = board.Position(board.Color.GOLD, 4, board.BLANK_BOARD)
            for mnum, full_move in enumerate(start):
                move = full_move[3:]
                if mnum < 2 and cfg.strict_setup is not None:
                    do_checks = cfg.strict_setup
                else:
                    do_checks = cfg.strict_checks
                try:
                    pos = pos.do_move_str(move, do_checks)
                except board.IllegalMove as exc:
                    print("Illegal move found \"%s\", %s" % (full_move, exc))
                    return 1
                eng.makemove(move)
        print(pos.board_to_str())

        for option, value in cfg.post_options:
            eng.setoption(option, value)

        if cfg.search_position:
            eng.go()

        while True:
            try:
                resp = eng.get_response(10)
                if resp.type == "info":
                    print(resp.message)
                elif resp.type == "log":
                    print("log: %s" % (resp.message, ))
                elif resp.type == "bestmove":
                    print("bestmove: %s" % (resp.move, ))
                    break
            except socket.timeout:
                if not cfg.search_position:
                    break

    finally:
        eng.quit()
        stop_waiting = time.time() + 20
        while time.time() < stop_waiting:
            try:
                resp = eng.get_response(1)
                if resp.type == "info":
                    print(resp.message)
                elif resp.type == "log":
                    print("log: %s" % (resp.message, ))
            except socket.timeout:
                try:
                    eng.quit()
                except IOError:
                    pass
            if not eng.is_running():
                break
        eng.cleanup()

    return 0


if __name__ == "__main__":
    main()
