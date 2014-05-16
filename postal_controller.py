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

import sys
import time

from ConfigParser import SafeConfigParser
from subprocess import Popen

import gameroom

LOG_FILE = "postal.log"

def log(message):
    print message
    plfile = open(LOG_FILE, "a")
    logline = [time.strftime("%Y-%m-%d %a %H:%M:%S")]
    logline.append(message)
    logline.append("\n")
    logline = " ".join(logline)
    plfile.write(logline)
    plfile.close()

def main():
    config = SafeConfigParser()
    try:
        config.readfp(open('gameroom.cfg', 'r'))
    except IOError:
        print "Could not open 'gameroom.cfg'."
        sys.exit(1)

    gameroom_url = config.get("global", "gameroom_url")
    bot_section = config.get("global", "default_engine")
    bot_name = config.get(bot_section, "username")
    bot_passwd = config.get(bot_section, "password")

    while True:
        try:
            open("stop_postal", 'r')
            log("Exiting after finding stop file")
            sys.exit()
        except IOError:
            pass
        gr_con = gameroom.GameRoom(gameroom_url)
        gr_con.login(bot_name, bot_passwd)
        games = gr_con.mygames()
        gr_con.logout()
        total_games = len(games)
        games = [g for g in games if g['postal'] == '1']
        postal_games = len(games)
        games = [g for g in games if g['turn'] == g['side']]
        my_turn_games = len(games)
        log("Found %d games with %d postal games and %d on my turn." % (
            total_games, postal_games, my_turn_games))
        if games:
            games.sort(key=lambda x: x['turnts'])
            for game_num, game in enumerate(games):
                try:
                    open("stop_postal", 'r')
                    log("Exiting after finding stop file")
                    sys.exit()
                except IOError:
                    pass
                log("%d/%d: Playing move against %s game #%s" % (
                        game_num+1, my_turn_games, game['player'], game['gid']))
                proc = Popen(["./gameroom.py", "move", game['gid']])
                proc.wait()
        else:
            log("No postal games with a turn found, sleeping.")
            time.sleep(300)

if __name__ == "__main__":
    main()
