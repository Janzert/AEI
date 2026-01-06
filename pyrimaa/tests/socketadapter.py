#!/usr/bin/env python
# Copyright (c) 2018 Brian Haskin Jr.
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

import argparse
import socket
import sys
from subprocess import PIPE, Popen
from threading import Event, Thread


class _ProcCom(Thread):
    def __init__(self, proc, socket):
        Thread.__init__(self)
        self.proc = proc
        self.stop = Event()
        self.socket = socket
        self.daemon = True

    def run(self):
        while not self.stop.is_set() and self.proc.poll() is None:
            msg = self.proc.stdout.readline()
            self.socket.sendall(msg.encode("utf-8"))


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description="Adapt socket communication.")
    parser.add_argument("--server")
    parser.add_argument("--port", type=int)
    parser.add_argument("--legacy", nargs=2)
    config = parser.parse_args(args)

    if config.legacy:
        address = (config.legacy[0], int(config.legacy[1]))
    else:
        address = (config.server, config.port)
    sock = socket.socket()
    sock.connect(address)

    proc = Popen("simple_engine", stdin=PIPE, stdout=PIPE, universal_newlines=True)
    com = _ProcCom(proc, sock)
    com.start()

    while proc.poll() is None:
        msg = sock.recv(4096)
        if len(msg) == 0:
            break
        proc.stdin.write(msg.decode("utf-8"))
        proc.stdin.flush()
    if proc.poll() is None:
        proc.stdin.write("quit\n")
        proc.stdin.flush()
    com.stop.set()
    sock.close()


if __name__ == "__main__":
    main()
