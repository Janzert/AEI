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

BB = long
BITS_ON_OFF_1 = 0xAAAAAAAAAAAAAAAAL
BITS_ON_OFF_2 = 0xCCCCCCCCCCCCCCCCL
BITS_ON_OFF_4 = 0xF0F0F0F0F0F0F0F0L
BITS_ON_OFF_8 = 0xFF00FF00FF00FF00L
BITS_ON_OFF_16 = 0xFFFF0000FFFF0000L
BITS_ON_OFF_32 = 0xFFFFFFFF00000000L

def bitandix(bitboard):
    """ get one set bit and the index of it from a 64bit int """
    bit = bitboard & (-bitboard)
    cnt = (bit & BITS_ON_OFF_1) != 0L
    cnt |= ((bit & BITS_ON_OFF_2) != 0L) << 1
    cnt |= ((bit & BITS_ON_OFF_4) != 0L) << 2
    cnt |= ((bit & BITS_ON_OFF_8) != 0L) << 3
    cnt |= ((bit & BITS_ON_OFF_16) != 0L) << 4
    cnt |= ((bit & BITS_ON_OFF_32) != 0L) << 5
    return (bit, cnt)

COL_GOLD = 0
COL_SILVER = 1

PC_RABBIT = 0
PC_CAT = 1
PC_DOG = 2
PC_HORSE = 3
PC_CAMEL = 4
PC_ELEPHANT = 5

NOT_A_FILE = BB(0x7F7F7F7F7F7F7F7F)
NOT_H_FILE = BB(0xFEFEFEFEFEFEFEFE)
NOT_1_RANK = BB(0xFFFFFFFFFFFFFF00)
NOT_8_RANK = BB(0x00FFFFFFFFFFFFFF)

TRAP_F3_IDX = 18
TRAP_C3_IDX = 21
TRAP_F6_IDX = 42
TRAP_C6_IDX = 45
TRAP_F3_BIT = BB(1) << 18
TRAP_C3_BIT = BB(1) << 21
TRAP_F6_BIT = BB(1) << 42
TRAP_C6_BIT = BB(1) << 45
TRAPS = BB(0x0000240000240000)

BASIC_SETUP = ((BB(0x00000000000000FF), BB(0x0000000000004200), BB(0x0000000000001800),
                BB(0x0000000000002400), BB(0x0000000000008000), BB(0x0000000000000100)),
               (BB(0xFF00000000000000), BB(0x0042000000000000), BB(0x0018000000000000),
                BB(0x0024000000000000), BB(0x0080000000000000), BB(0x0001000000000000)))

BLANK_BOARD = ((BB(0x0000000000000000), BB(0x0000000000000000), BB(0x0000000000000000),
                BB(0x0000000000000000), BB(0x0000000000000000), BB(0x0000000000000000)),
               (BB(0x0000000000000000), BB(0x0000000000000000), BB(0x0000000000000000),
                BB(0x0000000000000000), BB(0x0000000000000000), BB(0x0000000000000000)))

def neighbors_of(bits):
    """ get the neighboring bits to a set of bits """
    bitboard = (bits & NOT_H_FILE) >> 1
    bitboard |= (bits & NOT_A_FILE) << 1
    bitboard |= (bits & NOT_1_RANK) >> 8
    bitboard |= (bits & NOT_8_RANK) << 8
    return bitboard

def index_to_alg(cnt):
    """ Convert a bit index to algebraic notation """
    rank = "hgfedcba"[int(cnt % 8)]
    column = "12345678"[int(cnt // 8)]
    return rank + column

def alg_to_index(sqr):
    """ Convert algebraic notation to a bit index """
    index = 7-(ord(sqr[0])-97)
    index += (int(sqr[1])-1) * 8
    return index

MOVE_OFFSETS = [[[], []], [[], []]]
def _generate_move_offsets():
    for i in xrange(64):
        bit = BB(1) << i
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
def _genzobrist_newkey(used_keys, rnd):
    candidate = 0
    while candidate in used_keys:
        candidate = rnd.randint(-sys.maxint, sys.maxint)
    used_keys.append(candidate)
    return candidate

def _generate_zobrist_keys():
    rnd = random.Random()
    rnd.seed(0xF00F)
    used_keys = [0]
    for color in xrange(2):
        ZOBRIST_KEYS[0].append(_genzobrist_newkey(used_keys, rnd))
        ZOBRIST_KEYS[2].append([])
        for piece in xrange(6):
            ZOBRIST_KEYS[2][color].append([])
            for index in xrange(64):
                ZOBRIST_KEYS[2][color][piece].append(_genzobrist_newkey(used_keys, rnd))
            # Add zero key that won't change hash, used when adding and removing a piece from the board.
            ZOBRIST_KEYS[2][color][piece].append(0)
    for step in xrange(5):
        ZOBRIST_KEYS[1].append(_genzobrist_newkey(used_keys, rnd))
_generate_zobrist_keys()

ZOBRIST_KEYS = ZOBRIST_KEYS[2]

TRAP_NEIGHBORS = neighbors_of(TRAPS)

class Position(object):
    def __init__(self, sidemoving, steps_left, bitboards, placement_boards=None, zobrist=None):
        self.color = sidemoving
        self.stepsLeft = steps_left
        self.bitBoards = bitboards
        if placement_boards is None:
            placement_boards = []
            for side in bitboards:
                sideplaces = BB(0)
                for piece in side:
                    sideplaces |= piece
                placement_boards.append(sideplaces)

        self.placement = placement_boards

        if zobrist is None:
            #zobrist = ZOBRIST_KEYS[0][sideMoving] ^ ZOBRIST_KEYS[1][stepsLeft]
            zobrist = 0
            for color in xrange(2):
                for piece in xrange(6):
                    pieces = bitboards[color][piece]
                    while pieces:
                        p_bi = bitandix(pieces)
                        pieces ^= p_bi[0]
                        zobrist ^= ZOBRIST_KEYS[color][piece][p_bi[1]]

        self._zhash = zobrist

    def __eq__(self, other):
        try:
            #if self._zhash != other._zhash:
            #    return False
            if (self.color != other.color or
                self.stepsLeft != other.stepsLeft):
                return False
            #if self.placement != other.placement:
            #    return False
            if self.bitBoards != other.bitBoards:
                return False
        except:
            return False
        return True

    def __ne__(self, other):
        try:
            if self._zhash != other._zhash:
                return True
            if (self.color != other.color or
                self.stepsLeft != other.stepsLeft):
                return True
            if self.placement != other.placement:
                return True
            if self.bitBoards != other.bitBoards:
                return True
        except:
            return True
        return False

    def __cmp__(self, other):
        try:
            if self._zhash != other._zhash:
                return 1
            if (self.color != other.color or
                self.stepsLeft != other.stepsLeft):
                return 1
            if self.placement != other.placement:
                return 1
            if self.bitBoards != other.bitBoards:
                return 1
        except:
            return 1
        return 0

    def __hash__(self):
        return self._zhash

    def check_hash(self):
        """ Check to make sure the hash is correct """
        #sideMoving = self.color
        #stepsLeft = self.stepsLeft
        bitboards = self.bitBoards
        # zobrist = ZOBRIST_KEYS[0][sideMoving] ^ ZOBRIST_KEYS[1][stepsLeft]
        zobrist = 0
        for color in xrange(2):
            for piece in xrange(6):
                pieces = bitboards[color][piece]
                while pieces:
                    p_bi = bitandix(pieces)
                    pieces ^= p_bi[0]
                    zobrist ^= ZOBRIST_KEYS[color][piece][p_bi[1]]
        if zobrist != self._zhash:
            raise RuntimeError("hash value is incorrect.")

    def check_boards(self):
        """ Check the internal consistency of the bitboards """
        bitboards = self.bitBoards
        for side_ix, side in enumerate(bitboards):
            for i, board in enumerate(side[:-1]):
                for check_side_ix, check_side in enumerate(bitboards):
                    for check_board_ix, check_board in enumerate(check_side[i+1:]):
                        double = board
                        double &= check_board
                        if double != BB(0):
                            raise RuntimeError("Two pieces occupy one square, %s:%s %s:%s %s %s %s %s" % ("wb"[side_ix],
                                    "rcdhme"[i], "wb"[check_side_ix], "rcdhme"[check_board_ix], str(board),
                                    str(check_board), str(double), index_to_alg(bitandix(double)[1])))

        for i, side in enumerate(bitboards):
            placement = BB(0)
            for board in side:
                placement |= board
            if placement != self.placement[i]:
                raise RuntimeError("Placement boards are incorrect")

    def is_goal(self):
        """ Check to see if this position is goal for either side """
        ggoal = self.bitBoards[COL_GOLD][PC_RABBIT] & (~NOT_8_RANK)
        sgoal = self.bitBoards[COL_SILVER][PC_RABBIT] & (~NOT_1_RANK)
        if ggoal or sgoal:
            if self.color == COL_GOLD:
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
        grabbits = self.bitBoards[COL_GOLD][PC_RABBIT]
        srabbits = self.bitBoards[COL_SILVER][PC_RABBIT]
        if not grabbits or not srabbits:
            if self.color == COL_GOLD:
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
            if self.color == COL_GOLD:
                return -1
            else:
                return 1

        return False

    def to_long_str(self, dots=True):
        """ Generate long string representation of the position """
        bitBoards = self.bitBoards
        layout = [" +-----------------+"]
        for row in xrange(8, 0, -1):
            rows = ["%d| " % row]
            rix = 8*(row-1)
            for col in xrange(8):
                ix = rix+(7-col)
                bit = 1 << ix
                if bit & self.placement[0]:
                    piece = "* "
                    for pi in xrange(7):
                        if bit & bitBoards[0][pi]:
                            piece = "RCDHME"[pi] + " "
                            break
                    rows.append(piece)
                elif bit & self.placement[1]:
                    piece = "* "
                    for pi in xrange(7):
                        if bit & bitBoards[1][pi]:
                            piece = "rcdhme"[pi] + " "
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

    def to_short_str(self):
        """ Generate short string representation of the position """
        bitBoards = self.bitBoards
        placement = self.placement
        layout = ["["]
        for ix in xrange(63, -1, -1):
            bit = 1 << ix
            if bit & placement[0]:
                piece = "*"
                for pi in xrange(7):
                    if bit & bitBoards[0][pi]:
                        piece = "RCDHME"[pi]
                        break
                layout.append(piece)
            elif bit & placement[1]:
                piece = "*"
                for pi in xrange(7):
                    if bit & bitBoards[1][pi]:
                        piece = "rcdhme"[pi]
                        break
                layout.append(piece)
            else:
                layout.append(" ")
        layout.append("]")
        layout = "".join(layout)
        return layout

    def to_placing_move(self):
        """ Generate a placing move string representation of the position """
        whitestr = ["w"]
        for piece, pieceBoard in enumerate(self.bitBoards[COL_GOLD]):
            pname = "RCDHME"[piece]
            while pieceBoard:
                bi = bitandix(pieceBoard)
                sqr = index_to_alg(bi[1])
                whitestr.append(pname+sqr)
                pieceBoard ^= bi[0]
        whitestr = " ".join(whitestr)

        blackstr = ["b"]
        for piece, pieceBoard in enumerate(self.bitBoards[COL_SILVER]):
            pname = "rcdhme"[piece]
            while pieceBoard:
                bi = bitandix(pieceBoard)
                sqr = index_to_alg(bi[1])
                blackstr.append(pname+sqr)
                pieceBoard ^= bi[0]
        blackstr = " ".join(blackstr)

        return (whitestr, blackstr)

    def do_step(self, steps):
        """ Generate a new position from this position with the given steps """
        bitBoards = self.bitBoards
        placement = self.placement
        stepsLeft = self.stepsLeft
        color = self.color
        zobrist = self._zhash
        # make copies of the current boards
        if len(steps) == 1:
            if steps[0][3] == 0:
                newBoards = [[x for x in bitBoards[0]], bitBoards[1]]
            else:
                newBoards = [bitBoards[0], [x for x in bitBoards[1]]]
        else:
            newBoards = [[x for x in bitBoards[0]], [y for y in bitBoards[1]]]

        newPlacement = [placement[0], placement[1]]
        for (from_bit, from_in), (to_bit, to_in), step_piece, step_color in steps:
            # update the new bitboards
            newBoards[step_color][step_piece] ^= from_bit ^ to_bit
            newPlacement[step_color] ^= from_bit ^ to_bit
            # update the zobrist hash
            zobrist ^= ZOBRIST_KEYS[step_color][step_piece][from_in]
            zobrist ^= ZOBRIST_KEYS[step_color][step_piece][to_in]
            # remove trapped pieces, can only be one if any
            if (from_bit & TRAP_NEIGHBORS) and (newPlacement[step_color] & TRAPS):
                my_placement = newPlacement[step_color]
                trapped = 0
                if (my_placement & TRAP_C3_BIT) and (not (RMOVE_OFFSETS[21] & my_placement)):
                    trapped = TRAP_C3_BIT
                    trapped_idx = TRAP_C3_IDX
                elif (my_placement & TRAP_F3_BIT) and (not (RMOVE_OFFSETS[18] & my_placement)):
                    trapped = TRAP_F3_BIT
                    trapped_idx = TRAP_F3_IDX
                elif (my_placement & TRAP_C6_BIT) and (not (RMOVE_OFFSETS[45] & my_placement)):
                    trapped = TRAP_C6_BIT
                    trapped_idx = TRAP_C6_IDX
                elif (my_placement & TRAP_F6_BIT) and (not (RMOVE_OFFSETS[42] & my_placement)):
                    trapped = TRAP_F6_BIT
                    trapped_idx = TRAP_F6_IDX

                if trapped:
                    nottrapped = ~trapped
                    newPlacement[step_color] &= nottrapped
                    for piece in xrange(6):
                        if newBoards[step_color][piece] & trapped:
                            zobrist ^= ZOBRIST_KEYS[step_color][piece][trapped_idx]
                            newBoards[step_color][piece] &= nottrapped
                            break   # can only ever be one trapped piece
            stepsLeft -= 1
        if stepsLeft < 1:
            color ^= 1
            stepsLeft = 4

        return Position(color, stepsLeft, newBoards, newPlacement, zobrist)

    def do_move(self, steps):
        """ Generate a new position from the given move steps """
        steps = [step for step in steps if step[1][0] != 0] # remove trap steps, else they can add the piece back to the board.
        npos = self.do_step(steps)
        if npos.color == self.color:
            npos = Position((self.color+1)%2, 4, npos.bitBoards, npos.placement)
        return npos

    def get_single_steps(self):
        """ Generate all regular steps from this position """
        lbitandix = bitandix

        color = self.color
        bitBoards_my = self.bitBoards[color]
        bitBoards_opp = self.bitBoards[color ^1]
        placementBoards = self.placement
        zobrist = self._zhash

        newstepsleft = self.stepsLeft - 1
        if newstepsleft < 1:
            newcolor = color^1
            newstepsleft = 4
        else:
            newcolor = color

        move_list = []  # list to return generated steps in
        move_list_append = move_list.append
        empty_squares = ~(placementBoards[0] | placementBoards[1])
        stronger = placementBoards[color ^1] # stronger enemy pieces

        neighbors_of_my = neighbors_of(placementBoards[color])
        for piece in xrange(6):
            piecestomove = bitBoards_my[piece]
            stronger ^= bitBoards_opp[piece] # remove enemy of the same rank
            good_squares = neighbors_of_my | (~neighbors_of(stronger))
            piecestomove &= good_squares # get rid of frozen pieces

            while piecestomove:
                from_bi = lbitandix(piecestomove)
                piecestomove ^= from_bi[0]
                potential_squares = empty_squares & MOVE_OFFSETS[color][piece > 0][from_bi[1]]

                while potential_squares:
                    to_bi = lbitandix(potential_squares)
                    potential_squares ^= to_bi[0]

                    # create new position
                    # make copies of the current boards
                    if color == 0:
                        newBoards = [[x for x in bitBoards_my], bitBoards_opp]
                    else:
                        newBoards = [bitBoards_opp, [x for x in bitBoards_my]]
                    newPlacement = [placementBoards[0], placementBoards[1]]

                    # update the new bitboards
                    newBoards[color][piece] ^= from_bi[0] ^ to_bi[0]
                    newPlacement[color] ^= from_bi[0] ^ to_bi[0]
                    # update the zobrist hash
                    newzobrist = zobrist
                    newzobrist ^= ZOBRIST_KEYS[color][piece][from_bi[1]]
                    newzobrist ^= ZOBRIST_KEYS[color][piece][to_bi[1]]
                    # remove trapped pieces, can only be one if any
                    if (from_bi[0] & TRAP_NEIGHBORS) and (newPlacement[color] & TRAPS):
                        my_placement = newPlacement[color]
                        trapped = 0
                        if (my_placement & TRAP_C3_BIT) and (not (RMOVE_OFFSETS[21] & my_placement)):
                            trapped = TRAP_C3_BIT
                            trapped_idx = TRAP_C3_IDX
                        elif (my_placement & TRAP_F3_BIT) and (not (RMOVE_OFFSETS[18] & my_placement)):
                            trapped = TRAP_F3_BIT
                            trapped_idx = TRAP_F3_IDX
                        elif (my_placement & TRAP_C6_BIT) and (not (RMOVE_OFFSETS[45] & my_placement)):
                            trapped = TRAP_C6_BIT
                            trapped_idx = TRAP_C6_IDX
                        elif (my_placement & TRAP_F6_BIT) and (not (RMOVE_OFFSETS[42] & my_placement)):
                            trapped = TRAP_F6_BIT
                            trapped_idx = TRAP_F6_IDX

                        if trapped:
                            newPlacement[color] ^= trapped
                            for trappiece in xrange(6):
                                if newBoards[color][trappiece] & trapped:
                                    newzobrist ^= ZOBRIST_KEYS[color][trappiece][trapped_idx]
                                    newBoards[color][trappiece] ^= trapped
                                    break   # can only ever be one trapped piece

                    pos = Position(newcolor, newstepsleft, newBoards, newPlacement, newzobrist)

                    move_list_append((((from_bi, to_bi, piece, color), ), pos))

        return move_list

    def get_double_steps(self):
        """ Generate all push-pull steps from this position """
        lbitandix = bitandix
        do_step = self.do_step
        lneighbors_of = neighbors_of

        color = self.color
        opponent = color ^ 1
        bitboards_my = self.bitBoards[color]
        bitboards_opp = self.bitBoards[opponent]
        placement_boards = self.placement

        move_list = []
        move_list_append = move_list.append
        empty_squares = ~(placement_boards[0] | placement_boards[1])
        stronger = placement_boards[opponent] ^ bitboards_opp[0]

        neighbors_of_my = lneighbors_of(placement_boards[color])
        for piece in xrange(1, 6):
            piecestomove = bitboards_my[piece]
            stronger ^= bitboards_opp[piece]
            good_squares = neighbors_of_my | (~lneighbors_of(stronger))
            piecestomove &= good_squares    # eliminate frozen pieces

            for weaker in xrange(0, piece):
                victims = bitboards_opp[weaker] & lneighbors_of(piecestomove)

                while victims:
                    vic_bi = lbitandix(victims)
                    victims ^= vic_bi[0]
                    attackers = piecestomove & RMOVE_OFFSETS[vic_bi[1]]

                    victosqr = empty_squares & RMOVE_OFFSETS[vic_bi[1]]
                    # Get all push moves for this victim
                    while victosqr:
                        vto_bi = lbitandix(victosqr)
                        victosqr ^= vto_bi[0]
                        vicstep = (vic_bi, vto_bi, weaker, opponent)

                        # create list of possible push steps
                        pushattackers = attackers
                        while pushattackers:
                            attacker_bi = bitandix(pushattackers)
                            pushattackers ^= attacker_bi[0]

                            step = (vicstep, (attacker_bi, vic_bi, piece, color))
                            pos = do_step(step)

                            move_list_append((step, pos))

                    # Get all pull moves for this victim
                    while attackers:
                        attacker_bi = lbitandix(attackers)
                        attackers ^= attacker_bi[0]
                        atttosqr = empty_squares & RMOVE_OFFSETS[attacker_bi[1]]
                        vicstep = (vic_bi, attacker_bi, weaker, opponent)

                        while atttosqr:
                            ato_bi = bitandix(atttosqr)
                            atttosqr ^= ato_bi[0]

                            step = ((attacker_bi, ato_bi, piece, color), vicstep)
                            pos = do_step(step)

                            move_list_append((step, pos))

        return move_list

    def get_steps(self):
        """ Get all the steps from this position """
        steps = self.get_single_steps()
        if self.stepsLeft > 1:
            steps += self.get_double_steps()
        return steps

    def get_null_move(self):
        """ Generate a null move """
        return Position(self.color^1, 4, self.bitBoards, self.placement, self._zhash)

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
                            nextpart[move] = nsteps+step
                    elif move not in finished:
                        finished[move] = nsteps+step

                move = npos.get_null_move()
                if move not in finished:
                    finished[move] = nsteps
            partial = nextpart

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
                            nextpart[move] = nsteps+step
                    elif move not in finished:
                        finished[move] = nsteps+step

                move = npos.get_null_move()
                if move not in finished:
                    finished[move] = nsteps
            partial = nextpart

        return (finished, nodes)

    def get_rnd_step_move(self):
        """ Generate a move from this position by taking random steps. """
        pos = self
        taken = ()
        prevsteps = []
        while pos.color == self.color:
            steps = pos.get_steps()
            if pos.bitBoards != self.bitBoards:
                nullmove = pos.get_null_move()
                steps.append(((), nullmove))

            if len(steps) == 0: # If no steps were generated then we are immobilized.
                if pos == self:
                    return None
                else:
                    pos == self
                    continue

            randstep = random.choice(steps)
            taken += randstep[0]
            pos = randstep[1]

        return (taken, pos)

def add_traps(pos, steps):
    """ Add trap steps to a series of steps """
    tsteps = []
    for step in steps:
        tsteps.append(step)
        npos = pos.do_step((step, ))
        ntrap = neighbors_of(step[0][0]) & TRAPS
        if ntrap and (pos.placement[step[3]] & ntrap) and (not (npos.placement[step[3]] & ntrap)):
            for piece in xrange(0, 6):
                if pos.bitBoards[step[3]][piece] & ntrap:
                    tsteps.append((bitandix(ntrap), (0, 64), piece, step[3]))
                    break
        if (step[1][0] & TRAPS) and not (npos.placement[step[3]] & step[1][0]):
            tsteps.append((step[1], (0, 64), step[2], step[3]))
        pos = npos
    return tsteps

def steps_to_str(steps):
    """ Convert steps to a move string """
    pieces = "RCDHMErcdhme"
    move = []
    for step in steps:
        step_str = []
        step_str.append(pieces[step[2] + (step[3]*6)])
        if step[0][0] != 0:
            step_str.append(index_to_alg(step[0][1]))
            if step[1][0] == 0:
                step_str.append("x")
            else:
                direction = step[0][1] - step[1][1]
                if direction == 1:
                    step_str.append("e")
                elif direction == -1:
                    step_str.append("w")
                elif direction == 8:
                    step_str.append("s")
                elif direction == -8:
                    step_str.append("n")
                else:
                    step_str.append(',' + index_to_alg(step[1][1]))
        else:
            step_str.append(index_to_alg(step[1][1]))
        step_str = "".join(step_str)
        move.append(step_str)
    return " ".join(move)

def parse_move(line):
    """ Parse steps from a move string """
    text = line.split()
    if len(text) == 0:
        raise ValueError("No steps in move given to parse. %s" % (repr(line)))

    steps = []
    for step in text:
        piece = "RCDHMErcdhme".index(step[0])
        if piece > 5:
            piece -= 6
            color = COL_SILVER
        else:
            color = COL_GOLD
        index = alg_to_index(step[1:3])
        bit = BB(1) << index
        if len(step) > 3:
            if step[3] == 'x':
                steps.append(((bit, index), (0, 64), piece, color))
                continue
            elif step[3] == 'n':
                toindex = index + 8
            elif step[3] == 's':
                toindex = index - 8
            elif step[3] == 'e':
                toindex = index - 1
            elif step[3] == 'w':
                toindex = index + 1
            else:
                raise ValueError("Invalid step direction.")
            tobit = BB(1) << toindex
            steps.append(((bit, index), (tobit, toindex), piece, color))
        else:
            steps.append(((0, 64), (bit, index), piece, color))

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
    if text[0][movecolorix].lower() == 'b':
        color = COL_SILVER
    elif text[0][movecolorix].lower() == 'w':
        color = COL_GOLD
    else:
        raise ValueError("Could not find side to move")

    if len(text[0][movecolorix+1:]) > 0:
        raise NotImplementedError("Can not parse positions with steps already taken")
    else:
        steps = 4

    if text[1][0] != '+':
        raise ValueError("Board does not start after move line")
    ranknum = 7
    bitboards = list([list(x) for x in BLANK_BOARD])
    for line in text[2:10]:
        if not line[0].isdigit() or int(line[0])-1 != ranknum:
            raise ValueError("Unexpected rank number at rank %d" % ranknum+1)
        for piece_index in xrange(3, 18, 2):
            colnum = (piece_index-3)//2
            bit = 1 << ((ranknum*8) + (7-colnum))
            piecetext = line[piece_index]
            if piecetext in [' ', 'X', 'x', '.']:
                continue
            piece = "RCDHMErcdhme".find(piecetext)
            if piece != -1 and piece < 6:
                bitboards[0][piece] |= bit
            elif piece != -1:
                bitboards[1][piece-6] |= bit
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
            if pos.color == COL_GOLD:
                movenumber += 1

    return (movenumber, pos)

def parse_short_pos(side, stepsleft, text):
    """ Parse a position from a short format string """
    if side not in [COL_GOLD, COL_SILVER]:
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
                piececolor = COL_SILVER
            else:
                piececolor = COL_GOLD
            bit = BB(1) << (63-place)
            bitboards[piececolor][piece] |= bit
    pos = Position(side, stepsleft, bitboards)
    return pos

def test_random_play():
    """ Randomly plays games printing out each move. """
    total_turns = 0
    goal_wins = immo_wins = 0
    start_time = time.time()
    for i in xrange(100):
        pos = Position(COL_GOLD, 4, BASIC_SETUP)
        turn = 2
        while not pos.is_goal():
            moves = pos.get_moves()
            del moves[pos.get_null_move()]
            print turn
            print pos.to_long_str()
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
            if pos.color == COL_GOLD:
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
            if pos.color == COL_GOLD:
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
        pos = Position(COL_GOLD, 4, BASIC_SETUP)
        print pos.to_long_str()
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
            print pos.to_long_str()
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
        pos = parse_short_pos("wb".index(positiontext[0][-1]), 4, positiontext[1])
    else:
        movenum, pos = parse_long_pos(positiontext)
    print "%d%s" % (movenum, "wb"[pos.color])
    print
    print pos.to_long_str()
    print
    moves = pos.to_placing_move()
    print moves[0]
    print moves[1]
    print
    starttime = time.time()
    finished, nodes = pos.get_moves_nodes()
    del finished[pos.get_null_move()]
    print len(finished), "unique moves"
    gentime = time.time()

    score = 0
    tests = 1000
    for i in xrange(tests):
        if rnd_step_game(pos) == 1:
            score += 1
    endgames = time.time()

    print "Random step win percentage for gold is %.1f%%" % ((score/float(tests))*100)
    print "%.2f seconds to generate moves, %.2f seconds to play %d random games" % (gentime-starttime, endgames-gentime, tests)

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
    #    print move[0].to_short_str()
    #    print steps_to_str(add_traps(pos, move[1]))

if __name__ == "__main__":
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    if len(sys.argv) > 1:
        main(sys.argv[1])


