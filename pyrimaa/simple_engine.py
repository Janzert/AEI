#!/usr/bin/python
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

import exceptions
import sys
import time

from threading import Thread, Event
from Queue import Queue, Empty

from pyrimaa.board import (BASIC_SETUP, BLANK_BOARD, Color, parse_short_pos,
                           Position, IllegalMove)


class _ComThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.stop = Event()
        self.messages = Queue()
        self.setDaemon(True)

    def send(self, msg):
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()

    def run(self):
        # Hang onto AttributeError reference to survive into shutdown
        AttributeError = exceptions.AttributeError
        while not self.stop.isSet():
            try:
                msg = sys.stdin.readline()
            except AttributeError:
                # during shutdown sys will change to None
                return
            self.messages.put(msg.strip())


class AEIException(Exception):
    pass


class AEIEngine(object):
    def __init__(self, controller):
        self.strict_checks = True
        self.move_delay = None
        self.total_move_time = 0.0
        self.controller = controller
        try:
            header = controller.messages.get(30)
        except Empty:
            raise AEIException("Timed out waiting for aei header")
        if header != "aei":
            raise AEIException("Did not receive aei header, instead (%s)" %
                               (header))
        controller.send("protocol-version 1")
        controller.send("id name Sample Engine")
        controller.send("id author Janzert")
        controller.send("aeiok")
        self.newgame()

    def newgame(self):
        self.position = Position(Color.GOLD, 4, BLANK_BOARD)
        self.insetup = True

    def setposition(self, side_str, pos_str):
        side = "gswb".find(side_str) % 2
        self.position = parse_short_pos(side, 4, pos_str)
        self.insetup = False

    def setoption(self, name, value):
        std_opts = set(["tcmove", "tcreserve", "tcpercent", "tcmax", "tctotal",
                        "tcturns", "tcturntime", "greserve", "sreserve",
                        "gused", "sused", "lastmoveused", "moveused",
                        "opponent", "opponent_rating"])
        if name == "checkmoves":
            self.strict_checks = value.lower() in ["false", "no", "0"]
        elif name == "delaymove":
            self.move_delay = float(value)
        elif name not in std_opts:
            self.log("Warning: Received unrecognized option, %s" % (name))

    def makemove(self, move_str):
        try:
            self.position = self.position.do_move_str(move_str,
                                                      self.strict_checks)
        except IllegalMove as exc:
            self.log("Error: received illegal move %s" % (move_str,))
            return False
        if self.insetup and self.position.color == Color.GOLD:
            self.insetup = False
        return True

    def go(self):
        pos = self.position
        start_time = time.time()
        if self.insetup:
            setup = Position(Color.GOLD, 4, BASIC_SETUP)
            setup_moves = setup.to_placing_move()
            move_str = setup_moves[pos.color][2:]
        else:
            steps, result = pos.get_rnd_step_move()
            if steps is None:
                # we are immobilized, return an empty move
                move_str = ""
                self.log("Warning: move requested when immobilized.")
            else:
                move_str = pos.steps_to_str(steps)
        if self.move_delay:
            time.sleep(self.move_delay)
        move_time = time.time() - start_time
        self.total_move_time += move_time
        self.info("time %d" % (int(round(move_time),)))
        self.bestmove(move_str)

    def info(self, msg):
        self.controller.send("info " + msg)

    def log(self, msg):
        self.controller.send("log " + msg)

    def bestmove(self, move_str):
        self.controller.send("bestmove " + move_str)

    def main(self):
        ctl = self.controller
        while not ctl.stop.isSet():
            msg = ctl.messages.get()
            if msg == "isready":
                ctl.send("readyok")
            elif msg == "newgame":
                self.newgame()
            elif msg.startswith("setposition"):
                side, pos_str = msg.split(None, 2)[1:]
                self.setposition(side, pos_str)
            elif msg.startswith("setoption"):
                words = msg.split()
                name = words[2]
                v_ix = msg.find(name) + len(name)
                v_ix = msg.find("value", v_ix)
                if v_ix != -1:
                    value = msg[v_ix + 5:]
                else:
                    value = None
                self.setoption(name, value)
            elif msg.startswith("makemove"):
                move_str = msg.split(None, 1)[1]
                if not self.makemove(move_str):
                    return
            elif msg.startswith("go"):
                if len(msg.split()) == 1:
                    self.go()
            elif msg == "stop":
                pass
            elif msg == "quit":
                self.log("Debug: Exiting after receiving quit message.")
                if self.total_move_time > 0:
                    self.info("move gen time %f" % (self.total_move_time,))
                return


def main():
    ctl = _ComThread()
    ctl.start()
    try:
        eng = AEIEngine(ctl)
        eng.main()
    finally:
        ctl.stop.set()


if __name__ == "__main__":
    main()
