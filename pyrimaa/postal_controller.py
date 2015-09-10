#! /usr/bin/python
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

import ConfigParser
import logging
import optparse
import os.path
import sys
import time

from ConfigParser import SafeConfigParser

import gameroom

log = logging.getLogger("postal")


def main(args=sys.argv):
    opt_parser = optparse.OptionParser(
        usage="usage: %prog [-c CONFIG] [-b BOT]",
        description="Manage bot playing multiple postal games.")
    opt_parser.add_option('-c', '--config',
                          default="gameroom.cfg",
                          help="Configuration file to use.")
    opt_parser.add_option('-b', '--bot',
                          help="Bot section to use as the default.")
    options, args = opt_parser.parse_args(args)
    if len(args) > 1:
        print "Unrecognized command line arguments", args[1:]
        return 1
    config = SafeConfigParser()
    try:
        config.readfp(open(options.config, 'rU'))
    except IOError:
        print "Could not open '%s'." % (options.config, )
        return 1

    try:
        log_dir = config.get("postal", "log_dir")
    except ConfigParser.Error:
        try:
            log_dir = config.get("Logging", "directory")
        except ConfigParser.Error:
            log_dir = "."
    if not os.path.exists(log_dir):
        print "Log directory '%s' not found, attempting to create it." % (
            log_dir
        )
        os.makedirs(log_dir)

    try:
        log_filename = config.get("postal", "log_file")
    except ConfigParser.Error:
        log_filename = "postal-" + time.strftime("%Y-%m") + ".log"
    log_path = os.path.join(log_dir, log_filename)
    logfmt = logging.Formatter(fmt="%(asctime)s %(levelname)s: %(message)s",
                               datefmt="%Y-%m-%d %H:%M:%S")
    loghandler = logging.FileHandler(log_path)
    loghandler.setFormatter(logfmt)
    log.addHandler(loghandler)
    consolehandler = logging.StreamHandler()
    consolehandler.setFormatter(logfmt)
    log.addHandler(consolehandler)
    log.propagate = False
    gameroom.init_logging(config)

    gameroom_url = config.get("global", "gameroom_url")
    if options.bot:
        bot_section = options.bot
    else:
        bot_section = config.get("global", "default_engine")
    try:
        bot_username = config.get(bot_section, "username")
        bot_password = config.get(bot_section, "password")
    except ConfigParser.Error:
        try:
            bot_username = config.get("global", "username")
            bot_password = config.get("global", "password")
        except NoOptionError:
            log.error("Could not find username/password in config.")
            return 1

    while True:
        try:
            open("stop_postal", 'r')
            log.info("Exiting after finding stop file")
            sys.exit()
        except IOError:
            pass
        gr_con = gameroom.GameRoom(gameroom_url)
        gr_con.login(bot_username, bot_password)
        games = gr_con.mygames()
        gr_con.logout()
        total_games = len(games)
        games = [g for g in games if g['postal'] == '1']
        postal_games = len(games)
        games = [g for g in games if g['turn'] == g['side']]
        my_turn_games = len(games)
        log.info("Found %d games with %d postal games and %d on my turn." %
                 (total_games, postal_games, my_turn_games))
        if games:
            games.sort(key=lambda x: x['turnts'])
            for game_num, game in enumerate(games):
                try:
                    open("stop_postal", 'r')
                    log.info("Exiting after finding stop file")
                    sys.exit()
                except IOError:
                    pass
                log.info("%d/%d: Playing move against %s game #%s" %
                         (game_num + 1, my_turn_games, game['player'],
                          game['gid']))
                game_args = ["gameroom", "move", game['gid'], game['side']]
                if config.has_option("postal", game['gid']):
                    section = config.get("postal", game['gid'])
                    game_args += ["-b", section]
                    log.info("Using section %s for use with gid #%s" %
                             (section, game['gid']))
                elif config.has_option("postal", game['player']):
                    section = config.get("postal", game['player'])
                    game_args += ["-b", section]
                    log.info("Using section %s for use against %s" %
                             (section, game['player']))
                gmoptions = gameroom.parseargs(game_args)
                res = gameroom.run_game(gmoptions, config)
                if res is not None and res != 0:
                    log.warning("Error result from gameroom run %d." % (res, ))
        else:
            log.info("No postal games with a turn found, sleeping.")
            time.sleep(300)
