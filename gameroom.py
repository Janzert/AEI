#! /usr/bin/python
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

from ConfigParser import SafeConfigParser
import logging
import os
import os.path
import signal
import socket
import traceback
from subprocess import Popen, STDOUT
import sys
import re
import time
import urllib
import urllib2

from pyrimaa.aei import StdioEngine, SocketEngine, EngineController

_GR_CGI = "bot1gr.cgi"
_MY_HOST = "127.0.0.1"
_MY_PORT = 40007
_BOT_CON_TIMEOUT = 15

log = logging.getLogger("gameroom")
netlog = logging.getLogger("gameroom.net")
positionlog = logging.getLogger("gameroom.position")
enginelog = logging.getLogger("gameroom.engine")
console = None

class EngineCrashException(Exception):
    pass

def post(url, values, logname="network"):
    data = urllib.urlencode(values)
    req = urllib2.Request(url, data)
    tries = 0
    oldtimeout = socket.getdefaulttimeout()
    if values.get('wait', 0) != 0:
        socket.setdefaulttimeout(values['maxwait'] + 20)
    else:
        socket.setdefaulttimeout(300)
    try:
        try:
            response = urllib2.urlopen(req)
            body = response.read()
        except socket.timeout:
            body = ""
        while body == "" and tries < 6:
            if body == "":
                netlog.info("empty response from server will try again, sleeping for %d seconds", tries * 10)
                time.sleep(tries * 10)
            try:
                try:
                    response = urllib2.urlopen(req)
                    body = response.read()
                except socket.timeout:
                    body = ""
            except urllib2.URLError, err:
                try:
                    netlog.info("Received URLError, reason type %s", type(err.reason))
                    if err.reason[0] == 10060:
                        body = ""
                    else:
                        raise
                except (TypeError, AttributeError):
                    raise
            tries += 1
    finally:
        socket.setdefaulttimeout(oldtimeout)
    netlog.debug("%s response body:\n%s", logname, body)
    info = parsebody(body)
    if info.has_key('error'):
        log.error("Error in response to %s: %s", logname, info['error'])
    return parsebody(body)

def unquote(s):
    s = s.replace("%13", "\n")
    s = s.replace("%25", "%")
    return s

def parsebody(body):
    d = dict()
    lines = body.splitlines()
    for line in lines:
        eq = line.find('=')
        if eq > 0:
            k = line[:eq]
            d[k] = unquote(line[eq+1:])
    return d

class Table:
    def __init__(self, gameroom, tableinfo):
        self.min_move_time = 5
        self.min_timeleft = 5
        self.ponder = True
        self.gameroom = gameroom
        self.gid = tableinfo['gid']
        self.side = tableinfo['side']
        self.sid = None
        self.auth = ""
        self.state = {}
        self.sent_tc = {'tcmove': None, 'tcreserve': None, 'tcpercent': None,
                'tcmax': None, 'tctotal': None, 'tcturns': None, 'tcturntime': None}

    def _check_engine(self, timeout=None):
        if self.engine.engine.proc.poll() is not None:
            raise EngineCrashException("Process gone")
        try:
            response = self.engine.get_response(timeout)
            if response.type == "info":
                enginelog.info("%s", response.message)
            elif response.type == "log":
                if response.message.startswith("Error:"):
                    enginelog.error("%s", response.message)
                elif response.message.startswith("Warning:"):
                    enginelog.warn("%s", response.message)
                elif response.message.startswith("Debug:"):
                    enginelog.debug("%s", response.message)
                else:
                    enginelog.info("%s", response.message)
            return response
        except socket.timeout:
            raise
        except socket.error, exc:
            if (hasattr(exc, "args")
                and len(exc.args) > 0
                and exc.args[0] == 32):
                raise EngineCrashException("Socket reset")
            else:
                raise

    def _update_timecontrol(self, state):
        tc_vars = ['tcmove', 'tcreserve', 'tcpercent', 'tcmax', 'tctotal',
                'tcturns', 'tcturntime']
        for var in tc_vars:
            if state.has_key(var) and self.sent_tc.get(var, None) != state[var]:
                log.info("Sending %s of %s to engine.", var, state[var])
                self.engine.setoption(var, state[var])
                self.sent_tc[var] = state[var]

    def reserveseat(self):
        gameroom = self.gameroom
        values = dict(gid = self.gid,
                side = self.side,
                sid = gameroom.sid,
                action = "reserve")
        self.seat = post(gameroom.url, values, "Table.reserveseat")
        self.url = self.seat['base'] +'/'+ self.seat['cgi']

    def sitdown(self):
        values = dict(sid = self.seat['tid'],
                grid = self.seat['grid'],
                action = "sit")
        response = post(self.url, values, "Table.sitdown")
        self.sid = response['sid']

    def leave(self):
        values = dict(sid = self.sid,
                auth = self.auth,
                action = "leave")
        try:
            response = post(self.url, values, "Table.leave")
        except urllib2.URLError:
            return False
        try:
            ret = bool(int(response.get('ok', 0)))
        except ValueError:
            ret = False
        return ret

    def updatestate(self, wait = 0):
        lastchange = 0
        if (self.state
                and (self.state.get('lastchange', "") != "")):
            lastchange = self.state['lastchange']
        values = dict(sid = self.sid,
                what = "gamestate",
                wait = 0,
                lastchange = lastchange)
        if wait:
            values['wait'] = 1
            values['maxwait'] = wait
        gamestate = post(self.url, values, "Table.updatestate")
        if gamestate.get('auth', "") != "":
            self.auth = gamestate['auth']
        self.state = gamestate
        return gamestate

    def startgame(self):
        values = dict(sid = self.sid,
                action = "startmove",
                auth = self.auth)
        response = post(self.url, values, "Table.startgame")
        try:
            ret = bool(int(response.get('ok', 0)))
        except ValueError:
            ret = False
        return ret

    def move(self, move):
        values = dict(sid = self.sid,
                action = "move",
                move = move,
                auth = self.auth)
        if move.lower() == "resign":
            values['action'] = "resign"
            values['move'] = ""
        response = post(self.url, values, "Table.move")
        try:
            ret = bool(int(response.get('ok', 0)))
        except ValueError:
            ret = False
        return ret

    def chat(self, message):
        values = dict(sid = self.sid,
                action = "chat",
                chat = message,
                auth = self.auth)
        response = post(self.url, values, "Table.chat")
        try:
            ret = bool(int(response.get('ok', 0)))
        except ValueError:
            ret = False
        return ret

    def playgame(self, engine, greeting, onemove=False):
        self.engine = engine
        if self.side == 'w':
            opside = 'b'
        else:
            opside = 'w'
        opmove_re = re.compile(r"\b(\d+%s [^\n]+)\n[^\n]*$" % (opside))
        opplayer = opside + "player"
        state = self.updatestate()
        if (int(state.get('postal', "0"))
                and (state.get(opplayer, "") == ""
                    or state.get('turn', "") != self.side)):
            log.info("Postal game and it's not my turn")
            return

        engine.newgame()
        engine.isready()

        self._update_timecontrol(state)
        engine.isready()

        if len(state.get('moves', "")) > 4:
            log.info("Catching engine up to current move.")
            moves = state['moves'].splitlines()
            if len(moves) > 2:
                # the last move in the list is blank, i.e. the server is waiting for it
                if (state.get('turn', "") == self.side):
                    # the second to last move is also sent to the engine below
                    # when it's our turn so don't send it either now.
                    sendto = -2
                else:
                    sendto = -1
                for move in moves[:sendto]:
                    steps = move.split()[1:]
                    log.debug("sending move to engine: %s" % " ".join(steps))
                    engine.makemove(" ".join(steps))
                    engine.isready()

        if int(state.get('plycount', "0")) <= 1:
            # send a greeting if it's the first move of the game.
            self.chat(greeting)

        oplogged = False
        while state.get('result', "") == "":
            turnchange = time.time()
            while (state.get('result', "") == ""
                    and state.get('turn' "") != self.side):
                if onemove:
                    return
                try:
                    # eat any log, info, etc. messages the engine has sent
                    while True:
                        self._check_engine(0)
                except socket.timeout:
                    pass
                # XXX: This wait should probably really be based off the opponents time left
                state = self.updatestate(30)
                if not oplogged and state.get(opplayer, "") != "":
                    opname = state[opplayer]
                    if opname.startswith('*'):
                        opname = opname[2:]
                    log.info("Playing against %s", opname)
                    engine.setoption("opponent", opname)
                    engine.setoption("opponent_rating", state[opside+"rating"])
                    oplogged = True
                oppresent = opside + "present"
                if (state.get('starttime', "") == ""
                        and state.get(opplayer, "") != ""
                        and int(state.get(oppresent, "0")) < 1
                        and state.get('timecontrol', "") != ""):
                    while (time.time() - turnchange < 5*60
                            and int(state.get(oppresent, "0")) < 1):
                        time.sleep(10)
                        state = self.updatestate()
                    if int(state.get(oppresent, "0")) < 1:
                        log.info("%s left before game started", state[opplayer])
                        return
            if not oplogged and state.get(opplayer, "") != "":
                opname = state[opplayer]
                if opname.startswith('*'):
                    opname = opname[2:]
                log.info("Playing against %s", opname)
                oplogged = True
            if not oplogged and int(state.get('postal', "0")) < 1:
                # if the game hasn't started and not postal wait some more
                state = self.updatestate(300)
                continue
            gotmove = opmove_re.search(state.get('moves', ""))
            if gotmove:
                gotmove = gotmove.group(1)
                log.info("Received move %s", gotmove)
                enginemove = " ".join(gotmove.split()[1:])
                engine.makemove(enginemove)
            else:
                log.info("Starting game")
                self.startgame()
            positionlog.info("\n%s", state['position'])
            if state.get('result', "") == "":
                try:
                    # eat any log, info, etc. messages the engine has sent
                    while True:
                        self._check_engine(0)
                except socket.timeout:
                    pass
                tused_key = "%sused" % (self.side,)
                if state.has_key(tused_key):
                    moveused = int(state[tused_key])
                else:
                    moveused = 0
                starttime = time.time() - moveused
                engine.setoption("tcmoveused", moveused)
                engine.setoption("moveused", moveused)
                self._update_timecontrol(state)
                engine.setoption("wreserve", state['tcwreserve2'])
                engine.setoption("breserve", state['tcbreserve2'])
                if state.has_key('wused'):
                    engine.setoption("wused", state['wused'])
                if state.has_key('bused'):
                    engine.setoption("bused", state['bused'])
                if state.has_key('lastmoveused'):
                    engine.setoption("tclastmoveused", state['lastmoveused'])
                    engine.setoption("lastmoveused", state['lastmoveused'])
                engine.go()
                stopsent = False
                myreserve = "tc%sreserve2" % (self.side,)
                stoptime = starttime + int(state['tcmove']) + int(state[myreserve])
                if (state.has_key('turntime')
                    and (starttime + state['turntime']) < stoptime):
                    stoptime = int(starttime + state['turntime'])
                stoptime -= self.min_timeleft
                waittime = 10
                secondtimeupdate = False
                while True:
                    now = time.time()
                    if not stopsent and now + waittime > stoptime:
                        waittime = (stoptime - now) + 0.2
                        if waittime < 0:
                            waittime = 0
                    if not stopsent and now >= stoptime:
                        # try and get a move before time runs out
                        engine.stop()
                        log.info("Engine sent stop command to prevent timeout")
                        waittime = 10
                        stopsent = True
                    try:
                        response = self._check_engine(waittime)
                        if response.type == "bestmove":
                            break
                        if (response.type == "info"
                                and response.message.startswith("time")
                                and not secondtimeupdate):
                            engine.setoption("tcmoveused", int(time.time() - starttime))
                            secondtimeupdate = True
                    except socket.timeout:
                        pass
                engine.makemove(response.move)
                log.info("Sending move %s", response.move)
                endtime = time.time()
                if (self.min_move_time > endtime-starttime
                    and int(state.get('plycount', 0)) > 1):
                    stime = self.min_move_time - (endtime-starttime)
                    if stime > 0:
                        time.sleep(stime)
                self.move(response.move)
                if self.ponder and not stopsent:
                    engine.go("ponder")
                state = self.updatestate()
                positionlog.info("\n%s", state['position'])
        win = "I won"
        if state['result'].lower()[0] != self.side.lower():
            win = "I lost"
        log.info("Game over, %s result: '%s'", win, state['result'])

class GameRoom:
    def __init__(self, url):
        if url.endswith("/"):
            self.url = url + _GR_CGI
        else:
            self.url = url + "/" + _GR_CGI
        self.sid = None

    def login(self, username, password):
        values = dict(username = username,
                password = password,
                action = "login")
        response = post(self.url, values, "GameRoom.login")
        self.sid = response['sid']

    def logout(self):
        if not self.sid:
            log.warn("GameRoom.logout called before sid set.")
            return '0'
        values = dict(sid = self.sid, action = "leave")
        response = post(self.url, values, "GameRoom.logout")
        try:
            ret = bool(int(response['ok']))
        except KeyError:
            ret = False
        return ret

    def newgame(self, side, timecontrol="2/2/100/2/0", rated=False):
        if rated:
            rated = 1
        else:
            rated = 0

        if (side != 'b') and (side != 'w'):
            raise ValueError("Invalid value for side, %s" % (side))

        values = dict(timecontrol = timecontrol,
                rated = rated,
                side = side,
                sid = self.sid,
                action = "newGame")
        tableinfo = post(self.url, values, "GameRoom.newgame")
        tableinfo = parsebody(tableinfo.values()[0])
        return Table(self, tableinfo)

    def mygames(self):
        values = dict(sid = self.sid,
                what = "myGames")
        gamedata = post(self.url, values, "GameRoom.mygames")
        games = list()
        for gameid, gameinfo in gamedata.items():
            if re.match(r"\d+:[wb]", gameid):
                games.append(parsebody(gameinfo))
        return games

    def opengames(self):
        values = dict(sid = self.sid,
                what = "join")
        gamedata = post(self.url, values, "GameRoom.opengames")
        games = list()
        for gameid, gameinfo in gamedata.items():
            if re.match(r"\d+:[wb]", gameid):
                games.append(parsebody(gameinfo))
        return games

def parseargs(args):
    if len(args) < 2:
        return dict(against='', side='b', onemove=False)
    first = args[1].lower()
    if len(first) == 1 and first in "wb":
        return dict(against='', side=first, onemove=False)
    if first == "play" or first == "move":
        if len(args) < 3:
            raise ValueError("Not enough arguments given for command")
        ret = dict(against = args[2].lower())
        if len(args) > 3:
            ret['side'] = args[3].lower()
        else:
            ret['side'] = ""
        if first == "move":
            ret['onemove'] = True
        else:
            ret['onemove'] = False
        return ret
    raise ValueError("Bad commandline arguments")

def run_engine(botcmd, working_dir=None, address=(_MY_HOST, _MY_PORT)):
    listensock = socket.socket()
    while True:
        try:
            listensock.bind(address)
            listensock.listen(1)
            listensock.settimeout(_BOT_CON_TIMEOUT)
            log.debug("Listening for engine on %s:%d" % address)
            break
        except socket.error, exc:
            if (hasattr(exc, 'args')
                    and (exc.args[0] == 10048
                        or exc.args[0] == 98)):
                address = (address[0], address[1]+1)
            else:
                raise

    botargs = [botcmd]
    botargs += [str(x) for x in address]
    log.info("Starting engine with command '%s'", " ".join(botargs))
    bot_proc = Popen(botargs, cwd=working_dir)
    con = listensock.accept()
    log.debug("Engine connected.")
    engine = EngineController(SocketEngine(con))
    listensock.close()
    del listensock
    log.info("Engine initialized")
    engine.process = bot_proc

    return (engine, bot_proc)

def touch_run_file(run_dir, rfile):
    filename = os.path.join(run_dir, rfile)
    rf = open(filename, 'w')
    rf.write("%d\n" % os.getpid())
    rf.close()
    log.info("Created run file at %s" % filename)

def remove_run_files(run_dir, rfile):
    filename = os.path.join(run_dir, rfile)
    try:
        os.remove(filename)
    except OSError:
        pass
    log.info("Removed run file at %s" % filename)

def how_many_bots(run_dir):
    files = os.listdir(run_dir)
    count = 0
    for fn in files:
        if fn.endswith('.bot'):
            rf = open(os.path.join(run_dir, fn), 'r')
            try:
                pid = int(rf.read())
                if sys.platform == 'win32':
                    count += 1
                else:
                    try:
                        if os.kill(pid, signal.SIGCONT) > 0:
                            count += 1
                    except OSError:
                        pass
            except ValueError:
                pass
    return count

def already_playing(run_dir, gameid, side):
    isplaying = False
    runfn = os.path.join(run_dir, "%s%s.bot" % (gameid, side))
    try:
        rf = open(runfn, 'r')
        try:
            pid = int(rf.read())
            if sys.platform == 'win32':
                isplaying = True
            else:
                try:
                    if os.kill(pid, signal.SIGCONT) > 0:
                        isplaying = True
                except OSError:
                    pass
        except ValueError:
            pass
    except IOError:
        pass
    log.info("The file %s indicates we are already playing at %s on side %s" % (runfn, gameid, side))
    return isplaying

def str_loglevel(strlevel):
    strlevel = strlevel.lower()
    if strlevel == "debug":
        return logging.DEBUG
    elif strlevel == "info":
        return logging.INFO
    elif strlevel == "warning":
        return logging.WARNING
    elif strlevel == "error":
        return logging.ERROR
    else:
        raise ValueError("Unrecognised logging level")

def main(args):
    try:
        options = parseargs(args)
    except ValueError:
        print "Command not understood %s" % (" ".join(args))
        sys.exit(2)

    config = SafeConfigParser()
    try:
        config.readfp(open('gameroom.cfg', 'rU'))
    except IOError:
        print "Could not open 'gameroom.cfg' this file must be readable and contain the configuration for connecting to the gameroom."
        sys.exit(1)

    aeilog = logging.getLogger("gameroom.aei")
    if config.has_section("Logging"):
        logdir = config.get("Logging", "directory")
        if not os.path.exists(logdir):
            print "Log directory '%s' not found, attempting to create it." % (logdir)
            os.makedirs(logdir)
        logfilename = "%s-%s.log" % (time.strftime("%Y%m%d-%H%M"),
                    str(os.getpid()),
                    )
        logfilename = os.path.join(logdir, logfilename)
        if config.has_option("Logging", "level"):
            loglevel = str_loglevel(config.get("Logging", "level"))
        else:
            loglevel = logging.WARN

        logging.basicConfig(level = loglevel,
                filename = logfilename,
                datefmt="%Y-%m-%d %H:%M:%S",
                format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
                )

        if (config.has_option("Logging", "console")
            and config.getboolean("Logging", "console")):
            global console
            console = logging.StreamHandler()
            if config.has_option("Logging", "console_level"):
                conlevel = str_loglevel(config.get("Logging", "console_level"))
            else:
                conlevel = logging.INFO
            console.setLevel(conlevel)
            logging.getLogger('').addHandler(console)

        if config.has_option("Logging", "net_level"):
            netlevel = str_loglevel(config.get("Logging", "net_level"))
            netlog.setLevel(netlevel)

        if config.has_option("Logging", "engine_level"):
            enginelevel = str_loglevel(config.get("Logging", "engine_level"))
            enginelog.setLevel(enginelevel)

        if config.has_option("Logging", "aei_level"):
            aeilog.setLevel(str_loglevel(config.get("Logging", "aei_level")))

        positionlog.setLevel(logging.ERROR)
        if (config.has_option("Logging", "log_position")
            and config.getboolean("Logging", "log_position")):
            positionlog.setLevel(logging.INFO)


    run_dir = config.get("global", "run_dir")
    if not os.path.exists(run_dir):
        log.warn("Run file directory '%s' not found, attempting to create it." % (run_dir))
        os.makedirs(run_dir)
    bot_count = how_many_bots(run_dir)
    if bot_count >= config.getint("global", "max_bots"):
        log.info("Max number of bot limit %d reached, need to wait until some bots finish."
            % (config.getint("global", "max_bots")))
        return

    bot_section = config.get("global", "default_engine")
    com_method = config.get(bot_section, "communication_method").lower()
    enginecmd = config.get(bot_section, "cmdline")

    gameid_or_opponent = options['against']
    unknowns_caught = 0
    while True:
        try:
            if com_method == "2008cc":
                engine_ctl = EngineController(SocketEngine(enginecmd, legacy_mode=True))
            elif com_method == "socket":
                engine_ctl = EngineController(SocketEngine(enginecmd, log=aeilog))
            elif com_method == "stdio":
                engine_ctl = EngineController(StdioEngine(enginecmd, log=aeilog))
            else:
                raise ValueError("Unrecognized communication method, %s" % (com_method))
        except OSError, exc:
            log.error("Could not start the engine; exception thrown: %s", exc)
            sys.exit(1)

        try:
            for option in config.options(bot_section):
                if option.startswith("bot_"):
                    value = config.get(bot_section, option)
                    engine_ctl.setoption(option[4:], value)
                    log.info("Setting bot option %s = %s", option[4:], value)
            engine_ctl.isready()

            bot_username = config.get(bot_section, "username")
            bot_password = config.get(bot_section, "password")
            bot_greeting = config.get(bot_section, "greeting")

            gameroom = GameRoom(config.get("global", "gameroom_url"))
            gameroom.login(bot_username, bot_password)
            side = options['side']
            table = None
            if gameid_or_opponent == "":
                log.info("Starting a new game")
                if side == "":
                    side = 'b'
                tc = config.get(bot_section, "timecontrol")
                rated = config.getboolean(bot_section, "rated")
                log.info("Will play on side %s, using timecontrol %s" % (side, tc))
                table = gameroom.newgame(side, tc, rated)
            else:
                # look through my games for correct opponent and side
                games = gameroom.mygames()
                for game in games:
                    if (gameid_or_opponent == game['player'].lower()
                            or gameid_or_opponent == game['gid']):
                        if (side == "" or side == game['side']
                            and not already_playing(run_dir, game['gid'], game['side'])):
                            table = Table(gameroom, game)
                            log.info("Found in progress game")
                            break
                if table == None:
                    games = gameroom.opengames()
                    for game in games:
                        if (gameid_or_opponent == game['player'].lower()
                                or gameid_or_opponent == game['gid']):
                            if (side == "" or side == game['side']
                                and not already_playing(run_dir, game['gid'], game['side'])):
                                table = Table(gameroom, game)
                                log.info("Found game to join")
                                break
                if table == None:
                    log.error("Could not find game against %s with side '%s'", gameid_or_opponent, side)
                    engine_ctl.quit()
                    engine_ctl.cleanup()
                    break
            # Set the game to play in to current game id in case of a restart
            gameid_or_opponent = table.gid

            if options['against'] != "":
                joinmsg = "Joined game gid=%s side=%s; against %s" % (table.gid, table.side, options['against'])
            else:
                joinmsg = "Created game gid=%s side=%s; waiting for opponent" % (table.gid, table.side)
            log.info(joinmsg)
            if console is None:
                print joinmsg

            if config.has_option(bot_section, "ponder"):
                table.ponder = config.getboolean(bot_section, "ponder")
                if table.ponder:
                    log.info("Set pondering on.")
                else:
                    log.info("Set pondering off.")
            else:
                table.ponder = False
            if config.has_option("global", "min_move_time"):
                table.min_move_time = config.getint("global", "min_move_time")
                log.info("Set minimum move time to %d seconds.", table.min_move_time)
            else:
                table.min_move_time = 5
            if config.has_option("global", "min_time_left"):
                table.min_timeleft = config.getint("global", "min_time_left")
                log.info("Setting emergency stop time to %d seconds" % table.min_timeleft)
            else:
                table.min_timeleft = 5
        except:
            try:
                engine_ctl.quit()
            except (socket.error, IOError):
                pass
            for i in range(30):
                if engine_ctl.engine.proc.poll() is not None:
                    break
                time.sleep(1)
            else:
                log.warn("Engine did not exit in 30 seconds, terminating process")
                try:
                    if sys.platform == 'win32':
                        import ctypes
                        handle = int(engine_ctl.engine.proc._handle)
                        ctypes.windll.kernel32.TerminateProcess(handle, 0)
                    else:
                        os.kill(engine_ctl.engine.proc.pid, signal.SIGTERM)
                except os.error:
                    # don't worry about errors when trying to kill the engine
                    pass
            engine_ctl.cleanup()
            time.sleep(1)
            raise

        try:
            try:
                log.info("Joining game on %s side", table.side)
                table.reserveseat()
                table.sitdown()
                table.updatestate()
                engine_ctl.setoption("rated", table.state.get('rated', 1))
                try:
                    touch_run_file(run_dir, "%s%s.bot" % (table.gid, table.side))
                    time.sleep(1) # Give the server a small break.
                    log.info("Starting play")
                    table.playgame(engine_ctl, bot_greeting, options['onemove'])
                finally:
                    log.info("Leaving game")
                    remove_run_files(run_dir, "%s%s.bot" % (table.gid, table.side))
                    table.leave()
                break
            finally:
                try:
                    engine_ctl.quit()
                except (socket.error, IOError):
                    pass
                for i in range(30):
                    if engine_ctl.engine.proc.poll() is not None:
                        break
                    time.sleep(1)
                else:
                    log.warn("Engine did not exit in 30 seconds, terminating process")
                    try:
                        if sys.platform == 'win32':
                            import ctypes
                            handle = int(engine_ctl.engine.proc._handle)
                            ctypes.windll.kernel32.TerminateProcess(handle, 0)
                        else:
                            os.kill(engine_ctl.engine.proc.pid, signal.SIGTERM)
                    except os.error:
                        # don't worry about errors when trying to kill the engine
                        pass
                engine_ctl.cleanup()
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            raise
        except EngineCrashException, exc:
            log.error("Bot engine crashed (%s), restarting.", exc.args[0])
            time.sleep(1)
        except:
            unknowns_caught += 1
            log.error("Caught unkown exception #%d, restarting.\n%s" % (
                unknowns_caught, traceback.format_exc()))
            time.sleep(2);
            if unknowns_caught > 5:
                break


if __name__ == "__main__":
    main(sys.argv)

