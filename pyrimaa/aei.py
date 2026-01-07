import logging
import socket
import sys
import time
from queue import Empty, Queue
from subprocess import PIPE, Popen
from threading import Event, Thread

if sys.platform == "win32":
    import ctypes
    from collections import defaultdict


def _get_child_pids():
    class ProcessEntry(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.c_ulong),
            ("cntUsage", ctypes.c_ulong),
            ("th32ProcessID", ctypes.c_ulong),
            ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", ctypes.c_ulong),
            ("cntThreads", ctypes.c_ulong),
            ("th32ParentProcessID", ctypes.c_ulong),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.c_ulong),
            ("szExeFile", ctypes.c_char * 260),
        ]

    TH32CS_SNAPPROCESS = 0x2
    kernel32 = ctypes.windll.kernel32
    psnap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    childIDs = defaultdict(list)
    entry = ProcessEntry()
    entry.dwSize = ctypes.sizeof(ProcessEntry)
    kernel32.Process32First.argtypes = [ctypes.c_ulong, ctypes.POINTER(ProcessEntry)]
    if kernel32.Process32First(psnap, ctypes.byref(entry)) == 0:
        errno = kernel32.GetLastError()
        raise OSError(f"Received error from Process32First, {errno}")
    else:
        childIDs[entry.th32ParentProcessID].append(entry.th32ProcessID)
    while kernel32.Process32Next(psnap, ctypes.pointer(entry)):
        childIDs[entry.th32ParentProcessID].append(entry.th32ProcessID)
    errno = kernel32.GetLastError()
    if errno != 18:
        raise OSError(f"Received error from Process32Next, {errno}")
    kernel32.CloseHandle(psnap)
    return childIDs


def _kill_proc_tree(pid, cid_map=None):
    if cid_map is None:
        cid_map = _get_child_pids()
    if len(cid_map[pid]) > 0:
        for cid in cid_map[pid]:
            _kill_proc_tree(cid, cid_map)
    PROCESS_TERMINATE = 0x1
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if handle is not None:
        ctypes.windll.kernel32.TerminateProcess(handle, -1)
        ctypes.windll.kernel32.CloseHandle(handle)
    else:
        raise OSError(f"Could not kill process, {pid}")


START_TIME = 5.0
INIT_TIME = 15.0
STOP_TIME = 5.0


class EngineException(Exception):
    def __init__(self, message=None):
        self.message = message


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
        self.daemon = True

    def run(self):
        while not self.stop.is_set() and self.proc.poll() is None:
            msg = self.proc.stdout.readline()
            if self.log:
                self.log.debug(f"Received from bot: {repr(msg)}")
            self.outq.put(msg.strip())


class StdioEngine:
    def __init__(self, cmdline, log=None):
        proc = Popen(cmdline, shell=True, stdin=PIPE, stdout=PIPE, text=True)
        self.proc = proc
        self.log = log
        self.proc_com = _ProcCom(proc, log)
        self.proc_com.start()
        self.active = True

    def __del__(self):
        try:
            if self.active:
                self.cleanup()
        except AttributeError:
            pass

    def is_running(self):
        return self.proc.poll() is None

    def send(self, msg):
        if self.log:
            self.log.debug(f"Sending to bot: {repr(msg)}")
        self.proc.stdin.write(msg)
        self.proc.stdin.flush()

    def readline(self, timeout=None):
        try:
            msg = self.proc_com.outq.get(timeout=timeout)
        except Empty:
            raise socket.timeout() from None
        return msg

    def waitfor(self, expect, timeout=0.5):
        endtime = time.time() + timeout
        response = []
        while time.time() <= endtime:
            wait = endtime - time.time()
            try:
                line = self.readline(timeout=wait)
                response.append(line)
                if line.lstrip().lower().startswith(expect):
                    break
            except socket.timeout:
                pass
        else:
            raise EngineException("Engine did not respond in alloted time.")
        return response

    def cleanup(self):
        self.active = False
        self.proc_com.stop.set()
        if self.proc.poll() is None:
            if sys.platform == "win32":
                _kill_proc_tree(self.proc.pid)
            else:
                self.proc.terminate()
                stop_time = time.time() + STOP_TIME
                while time.time() < stop_time and self.proc.poll() is None:
                    pass
                if self.proc.poll() is None:
                    self.proc.kill()
        for stream in [self.proc.stdin, self.proc.stdout]:
            try:
                stream.close()
            except Exception:
                pass


class SocketEngine:
    def __init__(self, con, proc=None, legacy_mode=False, log=None):
        if len(con) != 2 or not hasattr(con[0], "settimeout"):
            address = ("127.0.0.1", 40015)
            listensock = socket.socket()
            while True:
                try:
                    listensock.bind(address)
                    listensock.listen(1)
                    listensock.settimeout(30)
                    break
                except OSError as exc:
                    if hasattr(exc, "args") and (
                        exc.args[0] == 10048 or exc.args[0] == 98
                    ):
                        address = (address[0], address[1] + 1)
                    else:
                        raise
            if legacy_mode:
                botargs = con + " 127.0.0.1 " + str(address[1])
            else:
                botargs = con + " --server 127.0.0.1 --port " + str(address[1])
            if con == "listen":
                print(f"Listening on {address[0]}:{address[1]}")
                proc = None
            else:
                proc = Popen(botargs, shell=True)
            con = listensock.accept()
            listensock.close()

        self.proc = proc
        self.log = log
        self.sock = con[0]
        self.address = con[1]
        self.buf = ""
        self.active = True

    def __del__(self):
        if self.active:
            self.cleanup()

    def is_running(self):
        return self.proc.poll() is None

    def send(self, msg):
        if self.log is not None:
            self.log.debug(f"Sending to bot: {repr(msg)}")
        self.sock.sendall(msg.encode("utf-8"))

    def readline(self, timeout=None):
        sock = self.sock
        buf = self.buf

        if buf:
            lineend = find_line_end(buf)
            if lineend != -1:
                self.buf = buf[lineend + 1 :]
                return buf[: lineend + 1].strip()

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
                packet = sock.recv(4096).decode("utf-8")
                if self.log:
                    self.log.debug(f"Received from bot: {repr(packet)}")
                response += packet
                if find_line_end(response) != -1:
                    break
            except socket.timeout:
                pass
            except OSError as exc:
                if hasattr(exc, "args") and (exc.args[0] == 10035 or exc.args[0] == 11):
                    pass
                else:
                    raise
            first = False
        else:
            raise socket.timeout()
        line = response[: find_line_end(response) + 1]
        self.buf = response[len(line) :]
        return line.strip()

    def waitfor(self, expect, timeout=0.5):
        endtime = time.time() + timeout
        response = []
        while time.time() <= endtime:
            wait = endtime - time.time()
            try:
                line = self.readline(timeout=wait)
                response.append(line)
                if line.lstrip().lower().startswith(expect):
                    break
            except socket.timeout:
                pass
        else:
            raise EngineException("Engine did not respond in alloted time.")
        return response

    def cleanup(self):
        self.active = False
        self.sock.close()
        if self.proc and self.proc.poll() is None:
            if sys.platform == "win32":
                _kill_proc_tree(self.proc.pid)
            else:
                self.proc.terminate()
                stop_time = time.time() + STOP_TIME
                while time.time() < stop_time and self.proc.poll() is None:
                    pass
                if self.proc.poll() is None:
                    self.proc.kill()


def get_engine(channel, cmd, logname=None):
    """Get the appropriate Engine for a given communication channel.
    Valid channel types are 'stdio', 'socket' and '2008cc'
    """
    if logname is not None:
        log = logging.getLogger(logname)
    else:
        log = None
    if channel == "stdio":
        engine = StdioEngine(cmd, log=log)
    elif channel == "socket":
        engine = SocketEngine(cmd, log=log)
    elif channel == "2008cc":
        engine = SocketEngine(cmd, legacy_mode=True, log=log)
    else:
        raise ValueError(f"Unrecognized channel given to get_engine ({channel})")
    return engine


class EngineResponse:
    def __init__(self, msg_type):
        self.type = msg_type


class EngineController:
    def __init__(self, engine):
        self.engine = engine
        try:
            engine.send("aei\n")
        except OSError as exc:
            raise EngineException("Could not send initial message to engine.") from exc
        try:
            response = engine.waitfor("aeiok", START_TIME)
        except socket.timeout as exc:
            raise EngineException("No aeiok received from engine.") from exc

        self.protocol_version = 0
        if response[0].lstrip().startswith("protocol-version"):
            version = response[0].lstrip().split()[1].strip()
            response = response[1:]
            self.protocol_version = 1
            if engine.log:
                if version != "1":
                    engine.log.warn(
                        f"Unrecognized protocol version from engine, {version}."
                    )
                engine.log.info("Setting aei protocol to version 1")

        self.ident = {}
        for line in response:
            line = line.lstrip()
            if line.startswith("id"):
                var, val = line[2:].strip().split(None, 1)
                self.ident[var] = val

        self.isready(INIT_TIME)

    def cleanup(self):
        self.engine.cleanup()

    def is_running(self):
        return self.engine.is_running()

    def _parse_resp(self, rstr):
        resp = EngineResponse(rstr.split()[0].lower())
        if resp.type == "info":
            resp.message = rstr[rstr.find("info") + len("info") :].strip()
        if resp.type == "log":
            resp.message = rstr[rstr.find("log") + len("log") :].strip()
        if resp.type == "bestmove":
            resp.move = rstr[rstr.find("bestmove") + len("bestmove") :].strip()
        return resp

    def get_response(self, timeout=None):
        rstr = self.engine.readline(timeout=timeout)
        if rstr == "":
            raise socket.timeout()
        return self._parse_resp(rstr)

    def isready(self, timeout=15):
        self.engine.send("isready\n")
        rstrs = self.engine.waitfor("readyok", timeout)
        if rstrs[-1].strip().lower() != "readyok":
            raise EngineException(f"Unexpected final response to isready ({rstrs[-1]})")
        responses = []
        for rstr in rstrs[:-1]:
            responses.append(self._parse_resp(rstr))
        return responses

    def newgame(self):
        self.engine.send("newgame\n")

    def makemove(self, move):
        self.engine.send(f"makemove {move}\n")

    def setposition(self, pos):
        side_colors = "wb"
        if self.protocol_version != 0:
            side_colors = "gs"
        self.engine.send(
            f"setposition {side_colors[pos.color]} {pos.board_to_str('short')}\n"
        )

    def go(self, searchtype=None):
        gocmd = ["go"]
        if searchtype == "ponder":
            gocmd.append(" ponder")
        gocmd.append("\n")
        gocmd = "".join(gocmd)
        self.engine.send(gocmd)

    def stop(self):
        self.engine.send("stop\n")

    def setoption(self, name, value=None):
        setoptcmd = f"setoption name {name}"
        if value is not None:
            setoptcmd += f" value {value}"
        self.engine.send(setoptcmd + "\n")

    def quit(self):
        self.engine.send("quit\n")
