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

import threading
import time
import socket
import sys

from threading import Thread, Event
from Queue import Queue, Empty
from subprocess import Popen, PIPE

START_TIME = 5.0
INIT_TIME = 15.0

class EngineException(Exception):
    pass

def find_line_end(posline):
    nloc = posline.find("\n")
    rloc = posline.find("\r")
    return max(nloc, rloc)

class _ProcCom(Thread):
    def __init__(self, proc, log):
        Thread.__init__(self)
        self.proc = proc
        self.log = log
        self.outq = Queue()
        self.stop = Event()
        self.setDaemon(True)

    def run(self):
        while not self.stop.isSet() and self.proc.poll() is None:
            msg = self.proc.stdout.readline()
            if self.log:
                self.log.debug("Received from bot: %s" % (repr(msg)))
            self.outq.put(msg.strip())

class StdioEngine:
    def __init__(self, cmdline, log=None):
        proc = Popen(cmdline,
                stdin = PIPE,
                stdout = PIPE,
                universal_newlines = True)
        self.proc = proc
        self.log = log
        self.proc_com = _ProcCom(proc, log)
        self.proc_com.start()

    def send(self, msg):
        if self.log:
            self.log.debug("Sending to bot: %s" % repr(msg))
        self.proc.stdin.write(msg)
        self.proc.stdin.flush()

    def readline(self, timeout=None):
        try:
            msg = self.proc_com.outq.get(timeout=timeout)
        except Empty:
            raise socket.timeout()
        return msg

    def waitfor(self, expect, timeout=0.5):
        endtime = time.time() + timeout
        response = []
        while time.time() <= endtime:
            wait = endtime - time.time()
            line = self.readline(timeout = wait)
            response.append(line)
            if line.lstrip().lower().startswith(expect):
                break
        else:
            raise EngineException(
                    "Engine did not respond in alloted time.")
        return response

    def cleanup(self):
        self.proc_com.stop.set()
        if self.proc.poll() is None:
            if sys.platform == 'win32':
                import ctypes
                handle = int(self.proc._handle)
                ctypes.windll.kernel32.TerminateProcess(handle, 0)
            else:
                os.kill(self.proc.pid, signal.SIGTERM)

class SocketEngine:
    def __init__(self, con, proc=None, legacy_mode=False, log=None):
        if (len(con) != 2
                or not hasattr(con[0], "settimeout")):
            address = ("127.0.0.1", 40015)
            listensock = socket.socket()
            while True:
                try:
                    listensock.bind(address)
                    listensock.listen(1)
                    listensock.settimeout(30)
                    break
                except socket.error, exc:
                    if (hasattr(exc, 'args')
                            and (exc.args[0] == 10048
                                or exc.args[0] == 98)):
                        address = (address[0], address[1]+1)
                    else:
                        raise
            if legacy_mode:
                botargs = [con]
                botargs += [str(a) for a in address]
            else:
                botargs = [con, "--server", "127.0.0.1", "--port"]
                botargs.append(str(address[1]))
            proc = Popen(botargs)
            con = listensock.accept()
            listensock.close()

        self.proc = proc
        self.log = log
        self.sock = con[0]
        self.address = con[1]
        self.buf = ""

    def send(self, msg):
        if self.log is not None:
            self.log.debug("Sending to bot: %s" % repr(msg))
        self.sock.sendall(msg)

    def readline(self, timeout=None):
        sock = self.sock
        buf = self.buf

        if buf:
            lineend = find_line_end(buf)
            if lineend != -1:
                self.buf = buf[lineend+1:]
                return buf[:lineend+1]

        if timeout is None:
            endtime = None
            sock.settimeout(None)
        else:
            endtime = time.time() + timeout
        response = buf
        first = True
        while first or endtime is None or time.time() <= endtime:
            try:
                if endtime is None:
                    sock.settimeout(None)
                else:
                    wait = endtime - time.time()
                    if wait < 0:
                        wait = 0
                    sock.settimeout(wait)
                packet = sock.recv(4096)
                if self.log:
                    self.log.debug("Received from bot: %s" % (repr(packet)))
                response += packet
                if find_line_end(response) != -1:
                    break
            except socket.timeout:
                pass
            except socket.error, exc:
                if (hasattr(exc, 'args')
                    and (exc.args[0] == 10035
                        or exc.args[0] == 11)):
                    pass
                else:
                    raise
            first = False
        else:
            raise socket.timeout()
        line = response[:find_line_end(response)+1]
        self.buf = response[len(line):]
        return line.strip()

    def waitfor(self, expect, timeout=0.5):
        endtime = time.time() + timeout
        response = []
        while time.time() <= endtime:
            wait = endtime - time.time()
            line = self.readline(timeout = wait)
            response.append(line)
            if line.lstrip().lower().startswith(expect):
                break
        else:
            raise EngineException(
                    "Engine did not respond in alloted time.")
        return response

    def cleanup(self):
        self.sock.close()

class EngineResponse:
    def __init__(self, type):
        self.type = type

class EngineController:
    def __init__(self, engine):
        self.gold_score = 0
        self.silver_score = 0

        self.engine = engine
        engine.send("aei\n")
        response = engine.waitfor("aeiok", START_TIME)

        self.ident = dict()
        for line in response:
            line = line.lstrip()
            if line.startswith('id'):
                var, val = line[2:].strip().split(None, 1)
                self.ident[var] = val

        self.isready(INIT_TIME)

    def cleanup(self):
        self.engine.cleanup()

    def get_response(self, timeout=None):
        rstr = self.engine.readline(timeout=timeout)
        resp = EngineResponse(rstr.split()[0].lower())
        if resp.type == "info":
            resp.message = rstr[rstr.find("info")+len("info"):].strip()
        if resp.type == "log":
            resp.message = rstr[rstr.find("log")+len("log"):].strip()
        if resp.type == "bestmove":
            resp.move = rstr[rstr.find("bestmove")+len("bestmove"):].strip()
        return resp

    def isready(self, timeout=15):
        self.engine.send("isready\n")
        self.engine.waitfor("readyok", timeout)

    def newgame(self):
        self.engine.send("newgame\n")

    def makemove(self, move):
        self.engine.send("makemove %s\n" % (move))

    def setposition(self, pos):
        self.engine.send("setposition %s %s\n" % (
                "wb"[pos.color],
                pos.to_short_str()))

    def go(self, searchtype=None, searchvalue=None):
        gocmd = ["go"]
        if searchtype == "ponder":
            gocmd.append(" ponder")
        elif searchtype == "infinite":
            gocmd.append(" infinite")
        gocmd.append("\n")
        gocmd = "".join(gocmd)
        self.engine.send(gocmd)

    def stop(self):
        self.engine.send("stop\n")

    def setoption(self, name, value=None):
        setoptcmd = "setoption name %s" % (name,)
        if value is not None:
            setoptcmd += " value %s" % (value,)
        self.engine.send(setoptcmd+"\n")

    def checkeval(self, pos=None):
        if pos is not None:
            self.engine.send("checkeval %s %s\n" % (
                "wb"[pos.color],
                pos.to_short_str()))
        else:
            self.engine.send("checkeval current\n")

    def quit(self):
        self.engine.send("quit\n")

