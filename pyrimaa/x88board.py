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

import random
import sys


class Color(object):
    GOLD = 0
    SILVER = 1


class Piece(object):
    EMPTY = 0
    GRABBIT = 1
    GCAT = 2
    GDOG = 3
    GHORSE = 4
    GCAMEL = 5
    GELEPHANT = 6
    SCOLOR = 8
    SRABBIT = 9
    SCAT = 10
    SDOG = 11
    SHORSE = 12
    SCAMEL = 13
    SELEPHANT = 14
    COUNT = 15
    PCHARS = " RCDHMExxrcdhme"
    DECOLOR = ~SCOLOR


def index_to_sq(ix):
    return ((ix // 16), (ix & 7))


def sq_to_index(sq):
    return (sq[0] * 16) + sq[1]


def index_to_alg(ix):
    """Convert an index to algebraic notation"""
    rank, column = index_to_sq(ix)
    return "abcdefgh" [column] + "12345678" [rank]


def alg_to_index(str):
    """Convert algebraic notation for a square to an index"""
    return sq_to_index((int(str[1]) - 1, "abcdefgh".index(str[0])))


def packed_to_index(ix):
    """Convert 0-63 index to 0x88 index"""
    return ix + (ix & ~7)


def index_to_packed(px):
    """Convert 0x88 index to 0-63 index"""
    return ((px & ~7) // 2) + (px & 7)


def bit_neighbors(bit):
    """ get the neighboring bits to a set of bits """
    bitboard = (bit & 0xFEFEFEFEFEFEFEFE) >> 1
    bitboard |= (bit & 0x7F7F7F7F7F7F7F7F) << 1
    bitboard |= (bit & 0xFFFFFFFFFFFFFF00) >> 8
    bitboard |= (bit & 0x00FFFFFFFFFFFFFF) << 8
    return bitboard


def bit_to_packed(bit):
    cnt = (bit & 0xAAAAAAAAAAAAAAAAL) != 0L
    cnt |= ((bit & 0xCCCCCCCCCCCCCCCCL) != 0L) << 1
    cnt |= ((bit & 0xF0F0F0F0F0F0F0F0L) != 0L) << 2
    cnt |= ((bit & 0xFF00FF00FF00FF00L) != 0L) << 3
    cnt |= ((bit & 0xFFFF0000FFFF0000L) != 0L) << 4
    cnt |= ((bit & 0xFFFFFFFF00000000L) != 0L) << 5
    return cnt


ALL_BITS = 0xFFFFFFFFFFFFFFFFL

ZOBRIST_KEYS = [0, [], []]


# generate zobrist keys, assuring no duplicate keys or 0
def _zobrist_newkey(used_keys, rnd):
    candidate = 0
    while candidate in used_keys:
        candidate = rnd.randint(-sys.maxint, sys.maxint)
    used_keys.append(candidate)
    return candidate


def _generate_zobrist_keys():
    rnd = random.Random()
    rnd.seed(0xF00F)
    used_keys = [0]
    ZOBRIST_KEYS[0] = _zobrist_newkey(used_keys, rnd)
    for piece in xrange(Piece.COUNT):
        ZOBRIST_KEYS[2].append([])
        for index in xrange(0x78):
            if piece == Piece.EMPTY:
                ZOBRIST_KEYS[2][piece].append(0)
            elif index & 0x88:
                ZOBRIST_KEYS[2][piece].append(0)
            else:
                ZOBRIST_KEYS[2][piece].append(_zobrist_newkey(used_keys, rnd))
    for step in xrange(5):
        ZOBRIST_KEYS[1].append(_zobrist_newkey(used_keys, rnd))


_generate_zobrist_keys()


class IllegalStepException(Exception):
    pass


class Position(object):
    def __init__(self, side, steps, board_array,
                 last_piece=Piece.EMPTY,
                 last_from=0x08,
                 inpush=False,
                 zobrist=None,
                 frozen=None):
        self.color = side
        self.steps = steps
        self.board = board_array
        self.last_piece = last_piece
        self.last_from = last_from
        self.in_push = inpush

        if frozen is None:
            offsets = (-1, 1, -16, 16)
            frozen = 0L
            for px in xrange(64):
                ix = packed_to_index(px)
                if board_array[ix] != Piece.EMPTY:
                    piece = board_array[ix]
                    strength = piece & Piece.DECOLOR
                    isfrozen = False
                    for o in offsets:
                        nix = ix + o
                        if nix & 0x88 or board_array[nix] == Piece.EMPTY:
                            continue
                        if not ((piece ^ board_array[nix]) & Piece.SCOLOR):
                            isfrozen = False
                            break
                        elif strength < board_array[nix] & Piece.DECOLOR:
                            isfrozen = True
                    if isfrozen:
                        frozen |= 1L << px
        self.frozen = frozen

        if zobrist is None:
            zobrist = ZOBRIST_KEYS[1][steps]
            if side:
                zobrist ^= ZOBRIST_KEYS[0]
            for rank in range(8):
                for col in range(8):
                    ix = sq_to_index((rank, col))
                    zobrist ^= ZOBRIST_KEYS[2][board_array[ix]][ix]
        self._zhash = zobrist

    def __eq__(self, other):
        try:
            if (self.color != other.color or self.steps != other.steps):
                return False
            if (self.last_from != other.last_from or
                self.last_piece != other.last_piece):
                return False
            if self.board != other.board:
                return False
        except:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self._zhash

    def is_goal(self):
        """Check to see if this position is a goal for either side"""
        board = self.board
        ggoal = False
        for ix in xrange(0x70, 0x78):
            if board[ix] == Piece.GRABBIT:
                ggoal = True
                break
        sgoal = False
        for ix in xrange(8):
            if board[ix] == Piece.SRABBIT:
                sgoal = True
                break
        if ggoal or sgoal:
            if self.color == Color.GOLD:
                if sgoal:
                    return -1
                else:
                    return 1
            else:
                if ggoal:
                    return 1
                else:
                    return -1
        else:
            return False

    def is_elimination(self):
        """Check to see if either side has lost all rabbits"""
        board = self.board
        gelim = True
        selim = True
        for rank in range(8):
            for col in range(8):
                ix = sq_to_index((rank, col))
                if board[ix] == Piece.GRABBIT:
                    gelim = False
                elif board[ix] == Piece.SRABBIT:
                    selim = False
            if not (gelim or selim):
                break
        if gelim or selim:
            if self.color == Color.GOLD:
                if gelim:
                    return -1
                else:
                    return 1
            else:
                if selim:
                    return 1
                else:
                    return -1
        else:
            return False

    def is_end(self):
        goal = self.is_goal()
        if goal:
            return goal
        elim = self.is_elimination()
        if elim:
            return elim
        if len(self.get_steps()) == 0:
            if self.color == Color.GOLD:
                return -1
            else:
                return 1
        return False

    def to_long_board(self, dots=True):
        """Generate long string representation of the board"""
        board = self.board
        piece_rep = Piece.PCHARS
        if dots:
            piece_rep = "." + piece_rep[1:]
        brepr = [" +-----------------+"]
        for rank in range(8, 0, -1):
            rank_rep = ["%d| " % rank]
            rix = sq_to_index((rank - 1, 0))
            for col in range(8):
                ix = rix + col
                piece = board[ix]
                if (piece == Piece.EMPTY and (rank in [3, 6]) and
                    (col in [2, 5])):
                    rank_rep.append("x")
                else:
                    rank_rep.append(piece_rep[piece])
                rank_rep.append(" ")
            rank_rep.append("|")
            brepr.append("".join(rank_rep))
        brepr.append(" +-----------------+")
        brepr.append("   a b c d e f g h  ")
        return "\n".join(brepr)

    def to_short_board(self):
        """Generate short string representation of the board"""
        board = self.board
        brepr = ["["]
        for rank in range(7, -1, -1):
            for col in range(8):
                ix = sq_to_index((rank, col))
                brepr.append(Piece.PCHARS[board[ix]])
        brepr.append("]")
        return "".join(brepr)

    def board_to_str(self, format="long", dots=True):
        if format == "long":
            return self.to_long_board(dots)
        elif format == "short":
            return self.to_short_board()
        else:
            raise ValueError("Invalid board format")

    def to_placing_moves(self):
        """Generate placing moves for this board"""
        board = self.board
        gmove = ["g"]
        smove = ["s"]
        for rank in range(8):
            for col in range(8):
                ix = sq_to_index((rank, col))
                piece = board[ix]
                if piece != Piece.EMPTY:
                    sq_str = [Piece.PCHARS[piece]]
                    sq_str.append(index_to_alg(ix))
                    sq_str = "".join(sq_str)
                    if piece & Piece.SCOLOR:
                        smove.append(sq_str)
                    else:
                        gmove.append(sq_str)
        return (" ".join(gmove), " ".join(smove))

    def place_piece(self, piece, index):
        if self.board[index] != Piece.EMPTY:
            raise ValueError("Tried to place a piece on another piece")
        newboard = [x for x in self.board]
        newboard[index] = piece
        zobrist = self._zhash ^ ZOBRIST_KEYS[2][piece][index]
        return Position(self.color, self.steps, newboard, zobrist=zobrist)

    def remove_piece(self, index):
        if self.board[index] == Piece.EMPTY:
            raise ValueError("Tried to remove empty piece")
        newboard = [x for x in self.board]
        piece = newboard[index]
        newboard[index] = Piece.EMPTY
        zobrist = self._zhash ^ ZOBRIST_KEYS[2][piece][index]
        return Position(self.color, self.steps, newboard, zobrist=zobrist)

    def do_step(self, step):
        """Generate a new position using the given step"""
        board = self.board
        if board[step[0]] == Piece.EMPTY:
            raise IllegalStepException("Tried to move from empty square %s" %
                                       index_to_alg(step[0]))
        if board[step[1]] != Piece.EMPTY:
            raise IllegalStepException("Tried to move to a full square %s" %
                                       index_to_alg(step[1]))
        offsets = (-1, 1, -16, 16)
        ispush = False
        ispull = False
        newfrom = step[0]
        piece = board[newfrom]
        pcolor = Color.GOLD
        if piece & Piece.SCOLOR:
            pcolor = Color.SILVER
        pstrength = piece & Piece.DECOLOR
        if pcolor == self.color:
            isfrozen = bool(self.frozen & (1L << index_to_packed(newfrom)))
            if isfrozen:
                print self.to_long_board()
                print hex(self.frozen)
                raise IllegalStepException(
                    "Tried to move frozen piece %s%s" %
                    (Piece.PCHARS[piece], index_to_alg(newfrom)))
            if pstrength == Piece.GRABBIT:
                illegal_dir = [-16, 16][pcolor]
                if step[1] == newfrom + illegal_dir:
                    raise IllegalStepException("Tried to move rabbit back %s" %
                                               index_to_alg(newfrom))
            if self.in_push and pstrength <= (self.last_piece & Piece.DECOLOR):
                raise IllegalStepException(
                    "Tried to finish push with weak piece %s%s" %
                    (Piece.PCHARS[piece], index_to_alg(newfrom)))
        else:
            if self.in_push:
                raise IllegalStepException(
                    "Tried to move opponent piece while in push %s%s to %s" %
                    (Piece.PCHARS[piece], index_to_alg(newfrom),
                     index_to_alg(step[1])))
            if (self.last_piece != Piece.EMPTY and step[1] == self.last_from
                and pstrength < (self.last_piece & Piece.DECOLOR)):
                ispull = True
            else:
                if self.steps > 2:
                    raise IllegalStepException("Tried to push on last step")
                stronger = False
                for noffset in [-1, 1, -16, 16]:
                    nix = newfrom + noffset
                    if (not (nix & 0x88) and board[nix] != Piece.EMPTY and
                        ((board[nix] ^ piece) & Piece.SCOLOR) and
                        pstrength < board[nix] & Piece.DECOLOR):
                        nstrength = board[nix] & Piece.DECOLOR
                        isfrozen = bool(self.frozen &
                                        (1L << index_to_packed(nix)))
                        if not isfrozen:
                            stronger = True
                            break
                if not stronger:
                    raise IllegalStepException(
                        "Tried to push without pusher %s%s" %
                        (Piece.PCHARS[piece], index_to_alg(newfrom)))
                ispush = True
        zobrist = (self._zhash ^ ZOBRIST_KEYS[2][piece][newfrom] ^
                   ZOBRIST_KEYS[1][self.steps])
        newboard = [s for s in board]
        newfrozen = self.frozen
        istrapped = False
        if step[1] in (0x22, 0x25, 0x52, 0x55):
            istrapped = True
            tix = step[1]
            for noff in [-1, 1, -16, 16]:
                nix = tix + noff
                if (not ((nix & 0x88) or nix == newfrom) and
                    board[nix] != Piece.EMPTY and
                    (not (board[nix] ^ piece) & Piece.SCOLOR)):
                    istrapped = False
                    break
        else:
            for tix in (0x22, 0x25, 0x52, 0x55):
                if board[tix] == Piece.EMPTY:
                    continue
                offset = step[0] - tix
                if offset not in offsets:
                    continue
                if (board[tix] ^ piece) & Piece.SCOLOR:
                    break
                captrap = True
                for toff in offsets:
                    if toff == offset:
                        continue
                    tnix = tix + toff
                    if tnix & 0x88 or board[tnix] == Piece.EMPTY:
                        continue
                    if not ((board[tnix] ^ board[tix]) & Piece.SCOLOR):
                        captrap = False
                        break
                if captrap:
                    zobrist ^= ZOBRIST_KEYS[2][board[tix]][tix]
                    cstrength = newboard[tix] & Piece.DECOLOR
                    px = index_to_packed(tix)
                    fn_bits = newfrozen & bit_neighbors(1L << px)
                    while fn_bits:
                        fnb = fn_bits & -fn_bits
                        fn_bits ^= fnb
                        nix = packed_to_index(bit_to_packed(fnb))
                        nstrength = newboard[nix] & Piece.DECOLOR
                        isfrozen = False
                        for noff in offsets:
                            nnix = nix + noff
                            if nnix & 0x88 or nnix == tix:
                                continue
                            if newboard[nnix] & Piece.DECOLOR > nstrength:
                                isfrozen = True
                                break
                        nbit = 1L << index_to_packed(nix)
                        if isfrozen:
                            newfrozen |= nbit
                        else:
                            newfrozen &= ~nbit
                    newboard[tix] = Piece.EMPTY
                break
        if not istrapped:
            newboard[step[1]] = piece
            zobrist ^= ZOBRIST_KEYS[2][piece][step[1]]
            for off in offsets:
                nix = step[1] + off
                if nix & 0x88 or newboard[nix] == Piece.EMPTY:
                    continue
                nbit = 1L << index_to_packed(nix)
                if not ((piece ^ newboard[nix]) & Piece.SCOLOR):
                    newfrozen &= ~nbit
                elif (not (newfrozen & nbit) and
                      (newboard[nix] & Piece.DECOLOR) < pstrength):
                    isfrozen = True
                    for noff in offsets:
                        nnix = nix + noff
                        if (nnix & 0x88 or nnix == nix or
                            newboard[nnix] == Piece.EMPTY):
                            continue
                        if (newboard[nnix] ^ piece) & Piece.SCOLOR:
                            isfrozen = False
                            break
                    if isfrozen:
                        newfrozen |= nbit
        for off in offsets:
            nix = newfrom + off
            if (nix & 0x88 or newboard[nix] == Piece.EMPTY):
                continue
            nbit = 1L << index_to_packed(nix)
            nstrength = newboard[nix] & Piece.DECOLOR
            if (newboard[nix] ^ piece) & Piece.SCOLOR:
                if newfrozen & nbit:
                    isfrozen = False
                    for noff in offsets:
                        nnix = nix + noff
                        if (nnix & 0x88 or nnix == newfrom or
                            newboard[nnix] == Piece.EMPTY):
                            continue
                        if newboard[nnix] & Piece.DECOLOR > nstrength:
                            isfrozen = True
                            break
                    if not isfrozen:
                        newfrozen ^= nbit
            else:
                isfrozen = False
                for noff in offsets:
                    nnix = nix + noff
                    if (nnix & 0x88 or nnix == newfrom or
                        newboard[nnix] == Piece.EMPTY):
                        continue
                    if not ((newboard[nnix] ^ piece) & Piece.SCOLOR):
                        isfrozen = False
                        break
                    elif nstrength < newboard[nnix] & Piece.DECOLOR:
                        isfrozen = True
                if isfrozen:
                    newfrozen |= nbit
        newboard[newfrom] = Piece.EMPTY
        fbit = 1L << index_to_packed(newfrom)
        newfrozen &= ~fbit
        newcolor = self.color
        newsteps = self.steps + 1
        if newsteps == 4:
            newsteps = 0
            newcolor ^= 1
            zobrist ^= ZOBRIST_KEYS[0]
            piece = Piece.EMPTY
            newfrom = 0x08
        zobrist ^= ZOBRIST_KEYS[1][newsteps]
        if self.in_push or ispull:
            piece = Piece.EMPTY
            newfrom = 0x08
        return Position(newcolor, newsteps, newboard, piece, newfrom, ispush,
                        zobrist, newfrozen)

    def do_move(self, steps):
        """Generate a new position from the given move"""
        npos = self
        for step in steps:
            npos = npos.do_step(step)
        if npos.color == self.color:
            npos = npos.get_null_move()

    def get_steps(self):
        """Get all steps from this position"""
        board = self.board
        steps = []
        if self.in_push:
            lastfrom = self.last_from
            lstrength = self.last_piece & Piece.DECOLOR
            for noffset in (-1, 1, -16, 16):
                pix = lastfrom + noffset
                if (pix & 0x88 or
                    ((board[pix] & Piece.SCOLOR) >> 3) != self.color):
                    continue
                pstrength = board[pix] & Piece.DECOLOR
                if pstrength > lstrength:
                    isfrozen = bool(self.frozen & (1L << index_to_packed(pix)))
                    if not isfrozen:
                        step = (pix, lastfrom)
                        steps.append((step, self.do_step(step)))
        else:
            lastcolor = (self.last_piece & Piece.SCOLOR) >> 3
            if (lastcolor == self.color and
                (self.last_piece & Piece.DECOLOR) > Piece.GRABBIT):
                # finish any possible pulls
                lastfrom = self.last_from
                lstrength = self.last_piece & Piece.DECOLOR
                for noff in [-1, 1, -16, 16]:
                    pix = lastfrom + noff
                    if (pix & 0x88) or board[pix] == Piece.EMPTY:
                        continue
                    if ((board[pix] ^ self.last_piece) & Piece.SCOLOR and
                        (board[pix] & Piece.DECOLOR) < lstrength):
                        step = (pix, lastfrom)
                        steps.append((step, self.do_step(step)))
            for rank in range(8):
                for col in range(8):
                    ix = sq_to_index((rank, col))
                    if board[ix] == Piece.EMPTY:
                        continue
                    pstrength = board[ix] & Piece.DECOLOR
                    if (board[ix] & Piece.SCOLOR) >> 3 == self.color:
                        isfrozen = bool(self.frozen &
                                        (1L << index_to_packed(ix)))
                        if not isfrozen:
                            to_offs = (-1, 1, -16, 16)
                            if pstrength == Piece.GRABBIT:
                                if self.color == Color.GOLD:
                                    to_offs = (-1, 1, 16)
                                else:
                                    to_offs = (-1, 1, -16)
                            for toff in to_offs:
                                tix = ix + toff
                                if (not (tix & 0x88) and
                                    board[tix] == Piece.EMPTY):
                                    step = (ix, tix)
                                    steps.append((step, self.do_step(step)))
                    elif self.steps < 3:
                        # start any pushes
                        haspusher = False
                        for noff in (-1, 1, -16, 16):
                            nix = ix + noff
                            if nix & 0x88:
                                continue
                            nstrength = board[nix] & Piece.DECOLOR
                            if (((board[ix] ^ board[nix]) & Piece.SCOLOR) and
                                nstrength > pstrength):
                                isfrozen = bool(self.frozen &
                                                (1L << index_to_packed(nix)))
                                if not isfrozen:
                                    haspusher = True
                                    break
                        if haspusher:
                            for poff in (-1, 1, -16, 16):
                                tix = ix + poff
                                if (not (tix & 0x88) and
                                    board[tix] == Piece.EMPTY):
                                    step = (ix, tix)
                                    steps.append((step, self.do_step(step)))
        return steps

    def get_null_move(self):
        """Get position with opposite side to move"""
        zobrist = self._zhash ^ ZOBRIST_KEYS[0]
        zobrist ^= ZOBRIST_KEYS[1][self.steps] ^ ZOBRIST_KEYS[1][0]
        return Position(self.color ^ 1, 0, self.board,
                        zobrist=zobrist,
                        frozen=self.frozen)

    def get_moves(self):
        """Generate all possible moves from this position"""
        color = self.color
        partial = {self: ()}
        finished = {}
        while partial:
            nextpart = {}
            for pos, steps in partial.iteritems():
                for step, npos in pos.get_steps():
                    if npos.color == color:
                        if npos not in nextpart:
                            nextpart[npos] = steps + step
                    elif npos not in finished:
                        finished[npos] = steps + step
                if not pos.in_push:
                    npos = pos.get_null_move()
                    if npos not in finished:
                        finished[npos] = steps
            partial = nextpart
        del finished[self.get_null_move()]
        return finished

    def steps_to_str(self, steps):
        """Convert steps to a move string"""
        dir_chars = {-1: "e", 1: "w", -16: "s", 16: "n"}
        pos = self
        move_rep = []
        for step in steps:
            step_rep = []
            step_rep.append(Piece.PCHARS[pos.board[step[0]]])
            step_rep.append(ix_to_alg(step[0]))
            direction = step[0] - step[1]
            try:
                step_rep.append(dir_chars[direction])
            except KeyError:
                step_rep.append("," + ix_to_alg(step[1]))
            move_rep.append("".join(step_rep))
            pos = pos.do_step(step)
            if pos.board[step[1]] == Piece.EMPTY:
                step_rep = [step_rep[0]]
                step_rep.append(ix_to_alg(step[1]))
                step_rep.append("x")
                move_rep.append("".join(step.rep))
        return " ".join(move_rep)


def parse_move(line):
    """Parse steps from a move string"""
    dir_offsets = {"e": -1, "w": 1, "s": -16, "n": 16}
    words = line.split()
    steps = []
    for step in words:
        if step[3] == 'x':
            continue
        piece = Piece.PCHARS.index(step[0])
        index = alg_to_index(step[1:3])
        try:
            tix = index + dir_offsets[step[3]]
        except KeyError:
            raise ValueError("Invalid step direction.")
        steps.append((index, tix))
    return steps


def parse_long_pos(text):
    """Parse a position from a long format string"""
    text = [l.strip() for l in text]
    for prenum, line in enumerate(text):
        if line or not line[0].isdigit():
            break
    text = text[prenum:]
    colorix = 0
    while text[0][colorix].isdigit():
        colorix += 1
    movenumber = int(text[0][:colorix])
    if text[0][colorix].lower() in "wg":
        color = Color.GOLD
    elif text[0][colorix].lower() in "bs":
        color = Color.SILVER
    else:
        raise ValueError("Could not find side to move")
    if text[0][colorix + 1:]:
        raise NotImplementedError(
            "Can not parse position with steps already taken")
    else:
        steps = 0

    if len(text) < 2 or text[1][0] != '+':
        raise ValueError("Board does not start after move line")
    rank = 7
    board = [Piece.EMPTY for x in xrange(0x80)]
    for line in text[2:10]:
        if not line[0].isdigit() or int(line[0]) - 1 != rank:
            raise ValueError("Unexpected rank number at rank %d" % rank + 1)
        for pc_index in xrange(3, 18, 2):
            col = (pc_index - 3) // 2
            ix = sq_to_index((rank, col))
            pc = line[pc_index]
            if pc in [' ', 'X', 'x', '.']:
                continue
            piece = Piece.PCHARS.find(pc)
            if piece == -1:
                raise ValueError("Invalid piece at %s" % (index_to_alg(ix)))
            board[ix] = piece
        rank -= 1
    pos = Position(color, steps, board)
    return (movenumber, pos)


def parse_short_pos(side, steps, text):
    """Parse a position from a short format string"""
    board = [Piece.EMPTY for x in xrange(0x80)]
    for place, piecetext in enumerate(text[1:-1]):
        if piecetext != ' ':
            try:
                piece = Piece.PCHARS.index(piecetext)
            except ValueError:
                raise ValueError("Invalid piece %s at position %d" %
                                 (piecetext, place))
            col = place % 8
            rank = 7 - (place // 8)
            ix = sq_to_index((rank, col))
            board[ix] = piece
    return Position(side, steps, board)


def main(filename):
    """Takes a filename and attempts to parse it as a position,
       then outputs a few statistics about the possible moves.
    """
    import time
    positionfile = open(filename, 'r')
    ptext = positionfile.readlines()
    if ptext[1][0] == '[':
        ptext = [l.strip() for l in ptext]
        movenum = int(ptext[0][:-1])
        side = "wbgs".index(ptext[0][-1]) % 2
        pos = parse_short_pos(side, 0, ptext[1])
    else:
        movenum, pos = parse_long_pos(ptext)
    print "%d%s" % (movenum, "gs" [pos.color])
    print
    print pos.to_long_board()
    print
    moves = pos.to_placing_moves()
    print moves[0]
    print moves[1]
    print
    steps = pos.get_steps()
    print len(steps), "initial steps"
    starttime = time.time()
    moves = pos.get_moves()
    print len(moves), "unique moves"
    gentime = time.time()

    print "%.2f seconds to generate moves" % (gentime - starttime)

    return

    import board
    mn, opos = board.parse_long_pos(ptext)
    omoves = opos.get_moves()
    del omoves[opos.get_null_move()]
    new_res = set([p.to_short_board() for p in moves.keys()])
    if len(new_res) != len(moves):
        print "duplicate boards in results %d!=%d" % (len(new_res), len(moves))
    old_res = set([p.to_short_str() for p in omoves.keys()])
    if new_res != old_res:
        print "Only in new results:"
        for upos, move in moves.iteritems():
            if upos.to_short_board() not in old_res:
                print pos.steps_to_str(move)
                print upos.to_short_board()
            if upos.color == pos.color:
                print "result position with same color"
            if upos.steps != 0:
                print "result position with steps taken"
            if (upos.last_piece != Piece.EMPTY or upos.last_from != 0x08):
                print "result position with last"
        print
        print "Only in old results:"
        for upos, move in omoves.iteritems():
            if upos.to_short_str() not in new_res:
                print board.steps_to_str(move)
                print upos.to_short_str()


if __name__ == "__main__":
    import os.path
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    if len(sys.argv) < 2:
        print "usage: %s <boardfile>" % os.path.basename(sys.argv[0])
        sys.exit(0)
    main(sys.argv[1])
