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

import sys
import random
import time

class Color:
    GOLD = 0
    SILVER = 1

class Piece:
    EMPTY = 0
    GRABBIT = 1
    GCAT = 2
    GDOG = 3
    GHORSE = 4
    GCAMEL = 5
    GELEPHANT = 6
    COLOR = 8
    SRABBIT = 9
    SCAT = 10
    SDOG = 11
    SHORSE = 12
    SCAMEL = 13
    SELEPHANT = 14
    COUNT = 15
    PCHARS = " RCDHMExxrcdhme"
    DECOLOR = ~COLOR

ALL_BITS = 0xFFFFFFFFFFFFFFFFL
NOT_A_FILE = 0xFEFEFEFEFEFEFEFEL
NOT_H_FILE = 0x7F7F7F7F7F7F7F7FL
NOT_1_RANK = 0xFFFFFFFFFFFFFF00L
NOT_8_RANK = 0x00FFFFFFFFFFFFFFL

TRAP_C3_IX = 18
TRAP_F3_IX = 21
TRAP_C6_IX = 42
TRAP_F6_IX = 45
TRAP_C3_BIT = 1L << 18
TRAP_F3_BIT = 1L << 21
TRAP_C6_BIT = 1L << 42
TRAP_F6_BIT = 1L << 45
TRAPS = 0x0000240000240000L

BASIC_SETUP = (0x0000FFFFFFFF0000L, 0x00000000000000FFL, 0x0000000000004200L, 0x0000000000001800L,
               0x0000000000002400L, 0x0000000000008000L, 0x0000000000000100L, None, None,
               0xFF00000000000000L, 0x0042000000000000L, 0x0018000000000000L,
               0x0024000000000000L, 0x0080000000000000L, 0x0001000000000000L)

BLANK_BOARD = (ALL_BITS, 0L, 0L, 0L, 0L, 0L, 0L, None, None, 0L, 0L, 0L, 0L, 0L, 0L)

def neighbors_of(bits):
    """ get the neighboring bits to a set of bits """
    bitboard = (bits & NOT_A_FILE) >> 1
    bitboard |= (bits & NOT_H_FILE) << 1
    bitboard |= (bits & NOT_1_RANK) >> 8
    bitboard |= (bits & NOT_8_RANK) << 8
    return bitboard

def bit_to_index(bit):
    """ get the index of a bit """
    cnt = (bit & 0xAAAAAAAAAAAAAAAAL) != 0L
    cnt |= ((bit & 0xCCCCCCCCCCCCCCCCL) != 0L) << 1
    cnt |= ((bit & 0xF0F0F0F0F0F0F0F0L) != 0L) << 2
    cnt |= ((bit & 0xFF00FF00FF00FF00L) != 0L) << 3
    cnt |= ((bit & 0xFFFF0000FFFF0000L) != 0L) << 4
    cnt |= ((bit & 0xFFFFFFFF00000000L) != 0L) << 5
    return cnt

def index_to_alg(cnt):
    """ Convert a bit index to algebraic notation """
    column = "abcdefgh"[int(cnt % 8)]
    rank = "12345678"[int(cnt // 8)]
    return column + rank

def alg_to_index(sqr):
    """ Convert algebraic notation to a bit index """
    index = ord(sqr[0])-97
    index += (int(sqr[1])-1) * 8
    return index

def index_to_sq(ix):
    """Convert an index to a column and rank"""
    return (ix % 8, ix // 8)

def sq_to_index(column, rank):
    """Convert a column and rank to an index"""
    return (rank * 8) + column

MOVE_OFFSETS = [[[], []], [[], []]]
def _generate_move_offsets():
    for i in xrange(64):
        bit = 1L << i
        moves = neighbors_of(bit)
        grmoves = moves
        if bit & NOT_1_RANK:
            grmoves ^= (bit >> 8)
        srmoves = moves
        if bit & NOT_8_RANK:
            srmoves ^= (bit << 8)
        MOVE_OFFSETS[0][1].append(moves)
        MOVE_OFFSETS[1][1].append(moves)
        MOVE_OFFSETS[0][0].append(grmoves)
        MOVE_OFFSETS[1][0].append(srmoves)
_generate_move_offsets()

RMOVE_OFFSETS = MOVE_OFFSETS[0][1]

ZOBRIST_KEYS = [[], [], []]

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
        for index in xrange(64):
            if piece == Piece.EMPTY:
                ZOBRIST_KEYS[2][piece].append(0)
            else:
                ZOBRIST_KEYS[2][piece].append(_zobrist_newkey(used_keys, rnd))
    for step in xrange(5):
        ZOBRIST_KEYS[1].append(_zobrist_newkey(used_keys, rnd))
_generate_zobrist_keys()

ZOBRIST_KEYS = ZOBRIST_KEYS[2]

TRAP_NEIGHBORS = neighbors_of(TRAPS)

class Position(object):
    def __init__(self, side, steps_left, bitboards, inpush=False,
            last_piece=Piece.EMPTY, last_from=None, placement=None, zobrist=None):
        self.color = side
        self.stepsLeft = steps_left
        self.bitBoards = bitboards
        self.inpush = inpush
        self.last_piece = last_piece
        self.last_from = last_from
        if placement is None:
            placement = [0L, 0L]
            for piece in range(Piece.GRABBIT, Piece.GELEPHANT+1):
                placement[Color.GOLD] |= bitboards[piece]
                placement[Color.SILVER] |= bitboards[piece | Piece.COLOR]
        self.placement = placement

        if zobrist is None:
            #zobrist = ZOBRIST_KEYS[0][sideMoving] ^ ZOBRIST_KEYS[1][stepsLeft]
            zobrist = 0
            for piece in xrange(Piece.COUNT):
                pieces = bitboards[piece]
                while pieces:
                    pbit = pieces & -pieces
                    pieces ^= pbit
                    pix = bit_to_index(pbit)
                    zobrist ^= ZOBRIST_KEYS[piece][pix]
        self._zhash = zobrist

    def __eq__(self, other):
        try:
            #if self._zhash != other._zhash:
            #    return False
            if (self.color != other.color or
                self.stepsLeft != other.stepsLeft):
                return False
            if (self.inpush != other.inpush
                    or self.last_from != other.last_from
                    or self.last_piece != other.last_piece):
                return False
            #if self.placement != other.placement:
            #    return False
            if self.bitBoards != other.bitBoards:
                return False
        except:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self._zhash

    def check_hash(self):
        """ Check to make sure the hash is correct """
        bitboards = self.bitBoards
        # zobrist = ZOBRIST_KEYS[0][sideMoving] ^ ZOBRIST_KEYS[1][stepsLeft]
        zobrist = 0
        for piece in xrange(Piece.COUNT):
            pieces = bitboards[piece]
            while pieces:
                pbit = pieces & -pieces
                pieces ^= pbit
                pix = bit_to_index(pbit)
                zobrist ^= ZOBRIST_KEYS[piece][pix]
        if zobrist != self._zhash:
            raise RuntimeError("hash value is incorrect.")

    def check_boards(self):
        """ Check the internal consistency of the bitboards """
        bitboards = self.bitBoards
        cplacement = [0L, 0L]
        empty = ALL_BITS
        for pnum, pboard in enumerate(bitboards):
            if pnum == 0 or pboard is None:
                continue
            for cnum, cboard in enumerate(bitboards[pnum+1:]):
                if cboard is None:
                    continue
                double = pboard & cboard
                if pboard & cboard:
                    print "%X %X %X %d %d" % (pboard, cboard, double, pnum, cnum)
                    raise RuntimeError("Two pieces occupy one square: %s %s" %
                            (Piece.PCHARS[pnum], Piece.PCHARS[cnum]))
            if pnum != 0:
                if (pnum ^ Piece.COLOR) & Piece.COLOR:
                    cplacement[0] |= pboard
                else:
                    cplacement[1] |= pboard
            empty &= ~pboard
        if cplacement != self.placement:
            if cplacement[0] != self.placement[0]:
                print "gplacement %X %X" % (cplacement[0], self.placement[0])
            if cplacement[1] != self.placement[1]:
                print "splacement %X %X" % (cplacement[1], self.placement[1])
            raise RuntimeError("Placement boards are incorrect")
        if empty != bitboards[0]:
            raise RuntimeError("Empty board is incorrect %X %X" % (bitboards[0], empty))

    def is_goal(self):
        """ Check to see if this position is goal for either side """
        ggoal = self.bitBoards[Piece.GRABBIT] & ~NOT_8_RANK
        sgoal = self.bitBoards[Piece.SRABBIT] & ~NOT_1_RANK
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

    def is_rabbit_loss(self):
        """ Check that both sides still have rabbits """
        grabbits = self.bitBoards[Piece.GRABBIT]
        srabbits = self.bitBoards[Piece.SRABBIT]
        if not grabbits or not srabbits:
            if self.color == Color.GOLD:
                if not grabbits:
                    return -1
                else:
                    return 1
            else:
                if not srabbits:
                    return 1
                else:
                    return -1
        else:
            return False

    def is_end_state(self):
        goal = self.is_goal()
        if goal:
            return goal
        norabbits = self.is_rabbit_loss()
        if norabbits:
            return norabbits
        if len(self.get_steps()) == 0:
            if self.color == Color.GOLD:
                return -1
            else:
                return 1
        return False

    def _to_long_str(self, dots=True):
        bitBoards = self.bitBoards
        layout = [" +-----------------+"]
        for row in xrange(8, 0, -1):
            rows = ["%d| " % row]
            rix = 8*(row-1)
            for col in xrange(8):
                ix = rix + col
                bit = 1 << ix
                if bit & (self.placement[0] | self.placement[1]):
                    piece = "* "
                    for pi in xrange(Piece.GRABBIT, Piece.COUNT):
                        if bitBoards[pi] is not None and bit & bitBoards[pi]:
                            piece = Piece.PCHARS[pi] + " "
                            break
                    rows.append(piece)
                else:
                    if (col == 2 or col == 5) and (row == 3 or row == 6):
                        rows.append("x ")
                    else:
                        if dots:
                            rows.append(". ")
                        else:
                            rows.append("  ")
            rows.append("|")
            rows = "".join(rows)
            layout.append(rows)
        layout.append(" +-----------------+")
        layout.append("   a b c d e f g h  ")
        return "\n".join(layout)

    def _to_short_str(self):
        bitBoards = self.bitBoards
        placement = self.placement[0] | self.placement[1]
        layout = ["["]
        for rank in xrange(7, -1, -1):
            rix = rank * 8
            for col in xrange(8):
                ix = rix + col
                bit = 1 << ix
                if bit & placement:
                    piece = "*"
                    for pi in xrange(Piece.GRABBIT, Piece.COUNT):
                        if bitBoards[pi] is not None and bit & bitBoards[pi]:
                            piece = Piece.PCHARS[pi]
                            break
                    layout.append(piece)
                else:
                    layout.append(" ")
        layout.append("]")
        layout = "".join(layout)
        return layout

    def board_to_str(self, format="long", dots=True):
        """Generate string representation of the board"""
        if format == "long":
            return self._to_long_str(dots)
        elif format == "short":
            return self._to_short_str()
        else:
            raise ValueError("Invalid board format")

    def to_placing_move(self, old_colors = False):
        """ Generate a placing move string representation of the position """
        if old_colors:
            color_str = "wb"
        else:
            color_str = "gs"
        whitestr = [color_str[Color.GOLD]]
        for piece, pieceBoard in enumerate(self.bitBoards[Piece.GRABBIT:Piece.GELEPHANT+1]):
            pname = Piece.PCHARS[piece + 1]
            while pieceBoard:
                bit = pieceBoard & -pieceBoard
                pieceBoard ^= bit
                pix = bit_to_index(bit)
                sqr = index_to_alg(pix)
                whitestr.append(pname+sqr)
        whitestr = " ".join(whitestr)

        blackstr = [color_str[Color.SILVER]]
        for piece, pieceBoard in enumerate(self.bitBoards[Piece.SRABBIT:Piece.SELEPHANT+1]):
            pname = Piece.PCHARS[(piece+1) | Piece.COLOR]
            while pieceBoard:
                bit = pieceBoard & -pieceBoard
                pieceBoard ^= bit
                pix = bit_to_index(bit)
                sqr = index_to_alg(pix)
                blackstr.append(pname+sqr)
        blackstr = " ".join(blackstr)
        return (whitestr, blackstr)

    def steps_to_str(self, steps):
        """Convert steps to a move string"""
        dir_chars = {1: "w", -1: "e", 8: "s", -8: "n"}
        pos = self
        move_rep = []
        for step in steps:
            step_rep = []
            from_bit = 1L << step[0]
            for piece in xrange(Piece.GRABBIT, Piece.COUNT):
                if (pos.bitBoards[piece] is not None
                        and pos.bitBoards[piece] & from_bit):
                    break
            if not pos.bitBoards[piece] & from_bit:
                raise ValueError("Tried to move empty piece")
            step_rep.append(Piece.PCHARS[piece])
            step_rep.append(index_to_alg(step[0]))
            direction = step[0] - step[1]
            try:
                step_rep.append(dir_chars[direction])
            except KeyError:
                step_rep.append("," + index_to_alg(step[1]))
            move_rep.append("".join(step_rep))
            npos = pos.do_step(step)
            trap = neighbors_of(from_bit) & TRAPS
            pcolor = (piece & Piece.COLOR) >> 3
            if ((pos.placement[pcolor] & trap or trap & (1L << step[1]))
                    and npos.bitBoards[Piece.EMPTY] & trap):
                tix = bit_to_index(trap)
                if tix == step[1]:
                    tpiece = piece
                else:
                    pcbit = pcolor << 3
                    for tpiece in xrange(Piece.GRABBIT | pcbit,
                            (Piece.GELEPHANT | pcbit) + 1):
                        if (pos.bitBoards[tpiece] is not None
                                and pos.bitBoards[tpiece] & trap):
                            break
                step_rep = [Piece.PCHARS[tpiece]]
                step_rep.append(index_to_alg(tix))
                step_rep.append("x")
                move_rep.append("".join(step_rep))
            pos = npos
        return " ".join(move_rep)

    def place_piece(self, piece, index):
        bit = 1L << index
        if self.placement[side] & bit:
            raise ValueError("Tried to place a piece on another piece")
        newBoards = [b for b in self.bitBoards]
        newPlacement = [self.placement[0], self.placement[1]]
        newBoards[piece] |= bit
        newPlacement[side] |= bit
        zobrist = self._zhash ^ ZOBRIST_KEYS[piece][index]
        return Position(self.color, self.stepsLeft, newBoards,
                placement=newPlacement, zobrist=zobrist)

    def remove_piece(self, index):
        bit = 1L << index
        if self.placement[Color.GOLD] & bit:
            side = Color.GOLD
        elif self.placement[Color.SILVER] & bit:
            side = Color.SILVER
        else:
            raise ValueError("Tried to remove non-existant piece")
        piece = Piece.GRABBIT
        while not (self.bitBoards[piece] & bit):
            piece += 1
        newBoards = [b for b in self.bitBoards]
        newPlacement = [self.placement[0], self.placement[1]]
        newBoards[piece] &= ~bit
        newPlacement[side] &= ~bit
        zobrist = self._zhash ^ ZOBRIST_KEYS[piece][index]
        return Position(self.color, self.stepsLeft, newBoards,
                placement=newPlacement, zobrist=zobrist)

    def check_step(self, step):
        class BadStep:
            def __init__(self, msg):
                self.message = msg
            def __str__(self):
                return self.message
            def __nonzero__(self):
                return False
        bitboards = self.bitBoards
        placement = self.placement
        from_bit = 1L << step[0]
        to_bit = 1L << step[1]
        if from_bit & bitboards[Piece.EMPTY]:
            return BadStep("Tried to move from an empty square")
        if not (to_bit & bitboards[Piece.EMPTY]):
            return BadStep("Tried to move to a non-empty square")
        for piece in range(Piece.GRABBIT, Piece.COUNT):
            if bitboards[piece] is not None and bitboards[piece] & from_bit:
                break
        direction = step[1] - step[0]
        from_neighbors = neighbors_of(from_bit)
        pcbit = piece & Piece.COLOR
        pcolor = pcbit >> 3
        pstrength = piece & Piece.DECOLOR
        if not neighbors_of(from_bit) & to_bit:
            return BadStep("Tried to move to non-adjacent square")
        if pcolor == self.color:
            isfrozen = (not from_neighbors & placement[pcolor]
                    and from_neighbors & placement[pcolor^1])
            if isfrozen:
                isfrozen = False
                for s in xrange((piece ^ Piece.COLOR) + 1,
                        (Piece.GELEPHANT | (pcbit ^ Piece.COLOR)) + 1):
                    if from_neighbors & bitboards[s]:
                        isfrozen = True
                        break
                if isfrozen:
                    return BadStep("Tried to move a frozen piece")
            if pstrength == Piece.GRABBIT:
                if ((pcolor == Color.GOLD and direction == -8)
                        or (pcolor == Color.SILVER and direction == 8)):
                    return BadStep("Tried to move a rabbit back")
            if self.inpush and pstrength <= self.last_piece & Piece.DECOLOR:
                return BadStep("Tried to push with too weak of a piece")
        else:
            if self.inpush:
                return BadStep("Tried to move opponent piece while already in push")
            if (self.last_piece == Piece.EMPTY
                    or self.last_from != step[1]
                    or pstrength >= self.last_piece & Piece.DECOLOR):
                if self.stepsLeft == 1:
                    return BadStep("Tried to start a push on the last step")
                stronger = False
                for s in xrange((piece ^ Piece.COLOR) + 1,
                        (Piece.GELEPHANT | (self.color << 3)) + 1):
                    if from_neighbors & bitboards[s]:
                        stronger = True
                        break
                if not stronger:
                    return BadStep("Tried to push a piece with no pusher around")
        return True

    def do_step(self, step):
        """ Generate a new position from this position with the given steps """
        bitBoards = self.bitBoards
        placement = self.placement
        stepsLeft = self.stepsLeft
        color = self.color
        zobrist = self._zhash
        newBoards = [b for b in bitBoards]
        newPlacement = [placement[0], placement[1]]
        from_ix = step[0]
        from_bit = 1L << from_ix
        to_ix = step[1]
        to_bit = 1L << to_ix
        pcolor = bool(placement[1] & from_bit)
        pcbit = pcolor << 3
        for piece in range(Piece.GRABBIT | pcbit, (Piece.GELEPHANT | pcbit) +1):
            if bitBoards[piece] & from_bit:
                break
        ispush = False
        ispull = False
        if pcolor != color:
            pstrength = piece & Piece.DECOLOR
            if (self.last_piece != Piece.EMPTY
                    and self.last_from == to_ix
                    and pstrength < (self.last_piece & Piece.DECOLOR)):
                ispull = True
            else:
                ispush = True
        # update the new bitboards
        step_bits = from_bit | to_bit
        newBoards[piece] ^= step_bits
        newPlacement[pcolor] ^= step_bits
        newBoards[Piece.EMPTY] ^= step_bits
        # update the zobrist hash
        zobrist ^= ZOBRIST_KEYS[piece][from_ix]
        zobrist ^= ZOBRIST_KEYS[piece][to_ix]
        # remove trapped pieces, can only be one if any
        ntrap = neighbors_of(from_bit) & TRAPS & ~neighbors_of(newPlacement[pcolor])
        if ntrap & newPlacement[pcolor]:
            nottrapped = ~ntrap
            tix = bit_to_index(ntrap)
            newBoards[Piece.EMPTY] |= ntrap
            newPlacement[pcolor] &= nottrapped
            for tpiece in xrange(Piece.GRABBIT | pcbit, (Piece.GELEPHANT | pcbit) + 1):
                if newBoards[tpiece] & ntrap:
                    zobrist ^= ZOBRIST_KEYS[tpiece][tix]
                    newBoards[tpiece] &= nottrapped
                    break   # can only ever be one trapped piece
        stepsLeft -= 1
        if stepsLeft < 1:
            color ^= 1
            stepsLeft = 4
            piece = Piece.EMPTY
            from_ix = None
        if self.inpush or ispull:
            piece = Piece.EMPTY
            from_ix = None
        return Position(color, stepsLeft, newBoards, ispush, piece, from_ix,
                placement=newPlacement, zobrist=zobrist)

    def do_move(self, steps):
        """ Generate a new position from the given move steps """
        for step in steps:
            npos = self.do_step(step)
        if npos.color == self.color:
            npos = Position((self.color+1)%2, 4, npos.bitBoards, placement=npos.placement)
        return npos

    def get_single_steps(self):
        """ Generate all regular steps from this position """
        color = self.color
        bitboards = self.bitBoards
        placementBoards = self.placement

        newstepsleft = self.stepsLeft - 1
        if newstepsleft < 1:
            newcolor = color^1
            newstepsleft = 4
        else:
            newcolor = color

        move_list = []  # list to return generated steps in
        move_list_append = move_list.append
        stronger = placementBoards[color ^1] # stronger enemy pieces
        neighbors_of_my = neighbors_of(placementBoards[color])
        pcbit = color << 3
        for piece in xrange(Piece.GRABBIT | pcbit, (Piece.GELEPHANT | pcbit) + 1):
            stronger ^= bitboards[piece ^ Piece.COLOR] # remove enemy of the same rank
            piecestomove = bitboards[piece] & (neighbors_of_my | ~neighbors_of(stronger))

            while piecestomove:
                from_bit = piecestomove & -piecestomove
                piecestomove ^= from_bit
                from_ix = bit_to_index(from_bit)
                potential_squares = bitboards[Piece.EMPTY] & MOVE_OFFSETS[color][(piece & Piece.DECOLOR) != Piece.GRABBIT][from_ix]

                while potential_squares:
                    to_bit = potential_squares & -potential_squares
                    potential_squares ^= to_bit
                    to_ix = bit_to_index(to_bit)
                    # create new position
                    # make copies of the current boards
                    newBoards = [b for b in bitboards]
                    newPlacement = [placementBoards[0], placementBoards[1]]
                    # update the new bitboards
                    step_bits = from_bit | to_bit
                    newBoards[Piece.EMPTY] ^= step_bits
                    newBoards[piece] ^= step_bits
                    newPlacement[color] ^= step_bits
                    # update the zobrist hash
                    zobrist = self._zhash
                    zobrist ^= ZOBRIST_KEYS[piece][from_ix]
                    zobrist ^= ZOBRIST_KEYS[piece][to_ix]
                    # remove trapped pieces, can only be one if any
                    if (from_bit & TRAP_NEIGHBORS) and (newPlacement[color] & TRAPS):
                        my_placement = newPlacement[color]
                        trapped = 0
                        if (my_placement & TRAP_C3_BIT) and (not (RMOVE_OFFSETS[TRAP_C3_IX] & my_placement)):
                            trapped = TRAP_C3_BIT
                            trapped_idx = TRAP_C3_IX
                        elif (my_placement & TRAP_F3_BIT) and (not (RMOVE_OFFSETS[TRAP_F3_IX] & my_placement)):
                            trapped = TRAP_F3_BIT
                            trapped_idx = TRAP_F3_IX
                        elif (my_placement & TRAP_C6_BIT) and (not (RMOVE_OFFSETS[TRAP_C6_IX] & my_placement)):
                            trapped = TRAP_C6_BIT
                            trapped_idx = TRAP_C6_IX
                        elif (my_placement & TRAP_F6_BIT) and (not (RMOVE_OFFSETS[TRAP_F6_IX] & my_placement)):
                            trapped = TRAP_F6_BIT
                            trapped_idx = TRAP_F6_IX

                        if trapped:
                            newBoards[Piece.EMPTY] ^= trapped
                            newPlacement[color] ^= trapped
                            for trappiece in xrange(Piece.GRABBIT | pcbit, (Piece.GELEPHANT | pcbit) + 1):
                                if newBoards[trappiece] & trapped:
                                    zobrist ^= ZOBRIST_KEYS[trappiece][trapped_idx]
                                    newBoards[trappiece] ^= trapped
                                    break

                    if newcolor == color:
                        pos = Position(newcolor, newstepsleft, newBoards,
                                False, piece, from_ix,
                                placement=newPlacement, zobrist=zobrist)
                    else:
                        pos = Position(newcolor, newstepsleft, newBoards,
                                False, Piece.EMPTY, None,
                                placement=newPlacement, zobrist=zobrist)
                    move_list_append(((from_ix, to_ix), pos))
        return move_list

    def get_steps(self):
        """ Get all the steps from this position """
        color = self.color
        bitboards = self.bitBoards
        placement = self.placement
        last_from = self.last_from
        neighbors_of_my = neighbors_of(self.placement[color])

        step_list = []
        if self.inpush:
            lastbit = 1L << last_from
            lf_neighbors = neighbors_of(lastbit)
            stronger = 0L
            attackers = 0L
            pcbit = color << 3
            lstrength = self.last_piece & Piece.DECOLOR
            for piece in xrange(Piece.GELEPHANT | pcbit, lstrength | pcbit, -1):
                attackers |= (bitboards[piece] & lf_neighbors
                        & (neighbors_of_my | ~neighbors_of(stronger)))
                stronger |= bitboards[piece ^ Piece.COLOR]
            while attackers:
                abit = attackers & -attackers
                attackers ^= abit
                step = (bit_to_index(abit), last_from)
                step_list.append((step, self.do_step(step)))
        else:
            opponent = color ^ 1
            stronger = placement[opponent] ^ bitboards[Piece.GRABBIT | (opponent << 3)]
            pcbit = color << 3
            attackers = 0L
            if self.stepsLeft > 1:
                for piece in xrange(Piece.GCAT | pcbit, (Piece.GELEPHANT | pcbit) +1):
                    stronger ^= bitboards[piece ^ Piece.COLOR]
                    attackers |= bitboards[piece] & (neighbors_of_my | ~neighbors_of(stronger))
            ocbit = opponent << 3
            empty_neighbors = neighbors_of(bitboards[Piece.EMPTY])
            for vpiece in xrange(Piece.GRABBIT | ocbit, Piece.GELEPHANT | ocbit):
                pullsdone = 0
                if self.last_piece & Piece.DECOLOR > vpiece & Piece.DECOLOR:
                    last_from = self.last_from
                    lastbit = 1L << last_from
                    pulls = bitboards[vpiece] & neighbors_of(lastbit)
                    pullsdone |= lastbit | pulls
                    while pulls:
                        pbit = pulls & -pulls
                        pulls ^= pbit
                        step = (bit_to_index(pbit), last_from)
                        step_list.append((step, self.do_step(step)))
                if self.stepsLeft < 2:
                    continue
                attackers &= ~bitboards[vpiece ^ Piece.COLOR]
                victims = (bitboards[vpiece] & neighbors_of(attackers)
                        & empty_neighbors)
                while victims:
                    vbit = victims & -victims
                    victims ^= vbit
                    vix = bit_to_index(vbit)
                    to_bits = neighbors_of(vbit) & bitboards[Piece.EMPTY]
                    while to_bits:
                        tbit = to_bits & -to_bits
                        to_bits ^= tbit
                        if (vbit & pullsdone) and (tbit & pullsdone):
                            continue
                        step = (vix, bit_to_index(tbit))
                        step_list.append((step, self.do_step(step)))

            step_list += self.get_single_steps()
        return step_list

    def get_null_move(self):
        """ Generate a null move """
        return Position(self.color^1, 4, self.bitBoards,
                placement=self.placement, zobrist=self._zhash)

    def get_moves(self):
        """ Generate all possible moves from this position """
        color = self.color
        partial = {self:()}
        partial_popitem = partial.popitem
        finished = {}
        while partial:
            nextpart = {}
            for npos, nsteps in partial.iteritems():
                for step, move in npos.get_steps():
                    if move.color == color:
                        if move not in nextpart:
                            nextpart[move] = nsteps + (step,)
                    elif move not in finished:
                        finished[move] = nsteps + (step,)
                if not npos.inpush:
                    move = npos.get_null_move()
                    if move not in finished:
                        finished[move] = nsteps
            partial = nextpart
        del finished[self.get_null_move()]
        return finished

    def get_moves_nodes(self):
        """ Generate all possible moves from this position, also keep track of
            and return the number of nodes visited while generating them. """
        color = self.color
        partial = {self:()}
        partial_popitem = partial.popitem
        finished = {}
        nodes = 0
        while partial:
            nextpart = {}
            for npos, nsteps in partial.iteritems():
                steps = npos.get_steps()
                nodes += len(steps)
                for step, move in steps:
                    if move.color == color:
                        if move not in nextpart:
                            nextpart[move] = nsteps + (step,)
                    elif move not in finished:
                        finished[move] = nsteps + (step,)
                if not npos.inpush:
                    move = npos.get_null_move()
                    if move not in finished:
                        finished[move] = nsteps
            partial = nextpart
        del finished[self.get_null_move()]
        return (finished, nodes)

    def get_rnd_step_move(self):
        """ Generate a move from this position by taking random steps. """
        pos = self
        taken = ()
        prevsteps = []
        while pos.color == self.color:
            steps = pos.get_steps()
            if pos != self:
                nullmove = pos.get_null_move()
                steps.append(((), nullmove))

            if len(steps) == 0: # If no steps were generated then we are immobilized.
                return None

            randstep = random.choice(steps)
            taken += randstep[0]
            pos = randstep[1]

        return (taken, pos)

def parse_move(line):
    """ Parse steps from a move string """
    text = line.split()
    if len(text) == 0:
        raise ValueError("No steps in move given to parse. %s" % (repr(line)))

    steps = []
    for step in text:
        from_ix = alg_to_index(step[1:3])
        if len(step) > 3:
            if step[3] == 'x':
                continue
            elif step[3] == 'n':
                to_ix = from_ix + 8
            elif step[3] == 's':
                to_ix = from_ix - 8
            elif step[3] == 'e':
                to_ix = from_ix - 1
            elif step[3] == 'w':
                to_ix = from_ix + 1
            else:
                raise ValueError("Invalid step direction.")
            steps.append((from_ix, to_ix))
        else:
            raise ValueError("Can't represent placing step")

    return steps

def parse_long_pos(text):
    """ Parse a position from a long format string """
    text = [x.strip() for x in text]
    for emptynum, line in enumerate(text):
        if line:
            break
    text = text[emptynum:]
    while text[0] and not text[0][0].isdigit():
        del text[0]
    movecolorix = 0
    while text[0][:movecolorix+1].isdigit():
        movecolorix += 1
    movenumber = int(text[0][:movecolorix])
    if text[0][movecolorix].lower() in "bs":
        color = Color.SILVER
    elif text[0][movecolorix].lower() in "wg":
        color = Color.GOLD
    else:
        raise ValueError("Could not find side to move")

    if len(text[0][movecolorix+1:]) > 0:
        raise NotImplementedError("Can not parse positions with steps already taken")
    else:
        steps = 4

    if text[1][0] != '+':
        raise ValueError("Board does not start after move line")
    ranknum = 7
    bitboards = [b for b in BLANK_BOARD]
    for line in text[2:10]:
        if not line[0].isdigit() or int(line[0])-1 != ranknum:
            raise ValueError("Unexpected rank number at rank %d" % ranknum+1)
        for piece_index in xrange(3, 18, 2):
            colnum = (piece_index-3)//2
            bit = 1 << ((ranknum*8) + colnum)
            piecetext = line[piece_index]
            if piecetext in [' ', 'X', 'x', '.']:
                continue
            piece = Piece.PCHARS.find(piecetext)
            if piece != -1:
                bitboards[piece] |= bit
                bitboards[Piece.EMPTY] &= ~bit
            else:
                raise ValueError("Invalid piece at %s%d" % ("abcdefgh"[colnum], ranknum+1))
        ranknum -= 1
    pos = Position(color, steps, bitboards)

    if len(text) > 12:
        for line in text[12:]:
            line = line.strip()
            if not line or line[0] == '#':
                break
            print "l", line
            line = " ".join(line.split()[1:])
            move = parse_move(line)
            pos = pos.do_step(move)
            if pos.color == Color.GOLD:
                movenumber += 1

    return (movenumber, pos)

def parse_short_pos(side, stepsleft, text):
    """ Parse a position from a short format string """
    if side not in [Color.GOLD, Color.SILVER]:
        raise ValueError("Invalid side passed into parse_short_str, %d" % (side))
    if stepsleft > 4 or stepsleft < 0:
        raise ValueError("Invalid steps left passed into parse_short_str, %d" % (stepsleft))

    bitboards = list([list(x) for x in BLANK_BOARD])
    for place, piecetext in enumerate(text[1:-1]):
        if piecetext != ' ':
            try:
                piece = "RCDHMErcdhme".index(piecetext)
            except ValueError:
                raise ValueError("Invalid piece at position %d, %s" % (place, piecetext))
            if piece > 5:
                piece -= 6
                piececolor = Color.SILVER
            else:
                piececolor = Color.GOLD
            index = (7 - (place // 8)) + (place % 8)
            bit = 1L << index
            bitboards[piececolor][piece] |= bit
    pos = Position(side, stepsleft, bitboards)
    return pos

def test_random_play():
    """ Randomly plays games printing out each move. """
    total_turns = 0
    goal_wins = immo_wins = 0
    start_time = time.time()
    for i in xrange(100):
        pos = Position(Color.GOLD, 4, BASIC_SETUP)
        turn = 2
        while not pos.is_goal():
            moves = pos.get_moves()
            del moves[pos.get_null_move()]
            print turn
            print pos.board_to_str()
            print len(moves)
            print (time.time()-start_time)
            print
            if len(moves) == 0:
                immo_wins += 1
                print "%d, %d win by immobilization. " % (i+1, immo_wins)
                break

            turn += 1
            pos = random.choice(moves.keys())

        total_turns += turn
        if len(moves) != 0:
            goal_wins += 1
            print "%d, %d win by goal." % (i+1, goal_wins)

    print total_turns/100.0, goal_wins, immo_wins, time.time()-start_time

def rnd_step_game(pos):
    while (not pos.is_goal()) and (not pos.is_rabbit_loss()):
        move = pos.get_rnd_step_move()
        if move is None: # immobilization
            assert len(pos.get_moves()) == 1
            if pos.color == Color.GOLD:
                return -1
            else:
                return 1

        pos = move[1]

    if pos.is_goal():
        return pos.is_goal()
    else:
        return pos.is_rabbit_loss()

def rnd_game(pos):
    while (not pos.is_goal()) and (not pos.is_rabbit_loss()):
        moves = pos.get_moves()
        del moves[pos.get_null_move()]
        if len(moves) == 0:
            if pos.color == Color.GOLD:
                return -1
            else:
                return 1

        pos = random.choice(moves.keys())

    if pos.is_goal():
        return pos.is_goal()
    else:
        return pos.is_rabbit_loss()

def test_rnd_steps():
    """ Randomly play games by choosing random steps. """
    total_turns = 0
    goal_wins = 0
    immo_wins = 0
    for i in xrange(100):
        pos = Position(Color.GOLD, 4, BASIC_SETUP)
        print pos.board_to_str()
        print

        turn = 3
        while not pos.is_goal():
            move = pos.get_rnd_step_move()
            if move is None: # immobilization
                print "Win by immobilization."
                moves = pos.get_moves()
                if len(moves) != 1: # Will contain illegal null move that doesn't change the position
                    print "Uh, oh. immo not immo."
                    print immo_wins
                    return
                immo_wins += 1
                break

            pos = move[1]
            print steps_to_str(move[0])
            print pos.board_to_str()
            print turn
            print
            turn += 1

        total_turns += turn
        if move is not None:
            print "Win by goal."
            goal_wins += 1

    print total_turns/100.0, goal_wins, immo_wins

def main(filename):
    """ Main entry point
        Takes a filename and attempts to parse it as a board position,
        then outputs a few statistics about the possible moves.
    """
    positionfile = open(filename, 'r')
    positiontext = positionfile.readlines()
    if positiontext[1][0] == '[':
        positiontext = [x.strip() for x in positiontext]
        movenum = int(positiontext[0][:-1])
        pos = parse_short_pos("wbgs".index(positiontext[0][-1]) % 2, 4, positiontext[1])
    else:
        movenum, pos = parse_long_pos(positiontext)
    print "%d%s" % (movenum, "gs"[pos.color])
    print
    print pos.board_to_str()
    print
    print pos.board_to_str("short")
    print
    placing = pos.to_placing_move()
    print placing[0]
    print placing[1]
    print
    starttime = time.time()
    moves, nodes = pos.get_moves_nodes()
    print len(moves), "unique moves"
    gentime = time.time()

    real_steps = [s for s, m in pos.get_steps()]
    for i in xrange(64):
        for j in xrange(64):
            tstep = (i, j)
            check_resp = pos.check_step(tstep)
            if check_resp and not tstep in real_steps:
                print "check_step thought %s to %s was valid step %d,%d" % (
                        index_to_alg(tstep[0]), index_to_alg(tstep[1]), tstep[0], tstep[1])
                return
            if not check_resp and tstep in real_steps:
                print "check_step thought %s to %s was invalid step" % (
                        index_to_alg(tstep[0]), index_to_alg(tstep[1]))
                return

    import x88board
    mn, opos = x88board.parse_long_pos(positiontext)
    omoves = opos.get_moves()
    new_res = set([p.board_to_str("short") for p in moves.keys()])
    if len(new_res) != len(moves):
        print "duplicate boards in results %d!=%d" % (len(new_res), len(moves))
        checked = {}
        for upos, move in moves.iteritems():
            bstr = upos.board_to_str("short")
            if checked.has_key(bstr):
                cpos = checked[bstr][0]
                print "found duplicate board"
                print pos.steps_to_str(move)
                print upos.board_to_str()
                print
                print pos.steps_to_str(checked[bstr][1])
                print cpos.board_to_str()
                print "upos inpush %s lf %s lp %s" % (
                        upos.inpush, upos.last_from, Piece.PCHARS[upos.last_piece])
                print "cpos inpush %s lf %s lp %s" % (
                        cpos.inpush, cpos.last_from, Piece.PCHARS[cpos.last_piece])
                if upos._zhash != cpos._zhash:
                    print "zobrist %X, %X" % (upos._zhash, cpos._zhash)
                if upos.placement != cpos.placement:
                    print "placement %s, %s" % (upos.placement, cpos.placement)
            else:
                checked[bstr] = (upos, move)
    old_res = set([p.board_to_str("short") for p in omoves.keys()])
    if new_res != old_res or len(omoves) != len(moves):
        discount = 0
        print "Only in new results:"
        for upos, move in moves.iteritems():
            if upos.board_to_str("short") not in old_res:
                discount += 1
                print pos.steps_to_str(move)
                print upos.board_to_str("short")
            if upos.color == pos.color:
                print "result position with same color"
            if upos.stepsLeft != 4:
                print "result position with steps taken"
            if upos.inpush:
                print "result position in push"
            if upos.last_from is not None or upos.last_piece != Piece.EMPTY:
                print "result position with last piece information"
            if discount > 40:
                print "Stopping results"
                break
        print
        print "Only in old results:"
        for upos, move in omoves.iteritems():
            if upos.board_to_str("short") not in new_res:
                print upos.steps_to_str(move)
                print upos.board_to_str("short")
                discount += 1
            if discount > 40:
                print "Stopping results"
                break
    """
    score = 0
    tests = 1000
    for i in xrange(tests):
        if rnd_step_game(pos) == 1:
            score += 1
    endgames = time.time()

    print "Random step win percentage for gold is %.1f%%" % ((score/float(tests))*100)
    print "%.2f seconds to generate moves, %.2f seconds to play %d random games" % (gentime-starttime, endgames-gentime, tests)
    """

    """
    score = 0
    tests = 1000
    for i in xrange(tests):
        if rnd_game(pos) == 1:
            score += 1

        print "\rRandom move win percentage after %d tests is %.4f" % (i+1, score/float(i+1)),

    print
    print "Random move win percentage for gold is %.4f" % (score/float(tests))
    """

    #allmoves = dict(finished)
    #for ix, move in enumerate(finished):
    #    omoves = move.get_moves()
    #    del omoves[move.get_null_move()]
    #    allmoves.update(omoves)
    #    if (ix+1) % 50 == 0:
    #        print (ix+1), len(allmoves)
    #print len(allmoves), "moves at 2 ply"

    #print
    #for move in finished.items():
    #    print move[0].board_to_str("short")
    #    print steps_to_str(add_traps(pos, move[1]))

if __name__ == "__main__":
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    if len(sys.argv) > 1:
        main(sys.argv[1])

