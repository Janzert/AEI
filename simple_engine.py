
import sys

from threading import Thread, Event
from Queue import Queue, Empty

from pyrimaa import board
from pyrimaa.board import Position, Color

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
        while not self.stop.isSet():
            msg = sys.stdin.readline()
            self.messages.put(msg.strip())


class AEIException(Exception):
    pass

class AEIEngine(object):
    def __init__(self, controller):
        self.controller = controller
        try:
            header = controller.messages.get(30)
        except Empty:
            raise AEIException("Timed out waiting for aei header")
        if header != "aei":
            raise AEIException("Did not receive aei header, instead (%s)" % (
                header))
        controller.send("protocol-version 1")
        controller.send("id name Sample Engine")
        controller.send("id author Janzert")
        controller.send("aeiok")
        self.newgame()

    def newgame(self):
        self.position = Position(Color.GOLD, 4, board.BLANK_BOARD)
        self.insetup = True

    def setposition(self, side_str, pos_str):
        side = "gswb".find(side_str) % 2
        self.position = board.parse_short_pos(side, 4, pos_str)
        self.insetup = False

    def setoption(self, name, value):
        std_opts = set(["tcmove", "tcreserve", "tcpercent", "tcmax", "tctotal",
                "tcturns", "tcturntime", "greserve", "sreserve", "gused",
                "sused", "lastmoveused", "moveused", "opponent",
                "opponent_rating"])
        if name not in std_opts:
            self.log("Warning: Received unrecognized option, %s" % (name))

    def makemove(self, move_str):
        self.position = self.position.do_move_str(move_str)
        if self.insetup and self.position.color == Color.GOLD:
            self.insetup = False

    def go(self):
        pos = self.position
        if self.insetup:
            setup = Position(Color.GOLD, 4, board.BASIC_SETUP)
            setup_moves = setup.to_placing_move()
            move_str = setup_moves[pos.color][2:]
        else:
            steps, result = pos.get_rnd_step_move()
            move_str = pos.steps_to_str(steps)
        self.bestmove(move_str)

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
                self.makemove(move_str)
            elif msg.startswith("go"):
                if len(msg.split()) == 1:
                    self.go()
            elif msg == "stop":
                pass
            elif msg == "quit":
                return

if __name__ == "__main__":
    ctl = _ComThread()
    ctl.start()
    try:
        eng = AEIEngine(ctl)
        eng.main()
    finally:
        ctl.stop.set()
    sys.exit()

