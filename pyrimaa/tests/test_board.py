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
# THE SOFTWARE

import random
import unittest

from pyrimaa import board

GOLD_GOAL_POS = """23w
 +-----------------+
8| r R r r   r r r |
7|     d           |
6|   D X c   X     |
5|         R m     |
4|                 |
3|     X     X     |
2|           d     |
1| R   R R R R     |
 +-----------------+
   a b c d e f g h""".splitlines()

SILVER_GOAL_POS = """23w
 +-----------------+
8| r   r r   r r r |
7|     d           |
6|   D X c   X     |
5|         R m     |
4|                 |
3|     X     X     |
2|           d     |
1| R   R R R R r   |
 +-----------------+
   a b c d e f g h""".splitlines()

DOUBLE_GOAL_POS = """23w
 +-----------------+
8| r R r r   r r r |
7|     d           |
6|   D X c   X     |
5|         R m     |
4|                 |
3|     X     X     |
2|           d     |
1| R   R R R R r   |
 +-----------------+
   a b c d e f g h""".splitlines()

GOLD_RABBIT_LOSS = """23w
 +-----------------+
8| r   r r   r r r |
7|     d           |
6|   D X c   X     |
5|           m     |
4|                 |
3|     X     X     |
2|           d     |
1|                 |
 +-----------------+
   a b c d e f g h""".splitlines()

SILVER_RABBIT_LOSS = """23w
 +-----------------+
8|                 |
7|     d           |
6|   D X c   X     |
5|         R m     |
4|                 |
3|     X     X     |
2|           d     |
1| R   R R R R     |
 +-----------------+
   a b c d e f g h""".splitlines()

DOUBLE_RABBIT_LOSS = """23w
 +-----------------+
8|                 |
7|     d           |
6|   D X c   X     |
5|           m     |
4|                 |
3|     X     X     |
2|           d     |
1|                 |
 +-----------------+
   a b c d e f g h""".splitlines()

DOUBLE_IMMOBILIZATION_POS = """23w
 +-----------------+
8| r E m H         |
7| R d H           |
6|   C X     X     |
5|                 |
4|                 |
3|     X     X c   |
2|           h D r |
1|         h M e R |
 +-----------------+
   a b c d e f g h""".splitlines()

INDUCE_NULL_MOVE_POS = """8w
 +-----------------+
8| r r r r   r r r |
7|     h r e h     |
6|   d c C   d     |
5|       c R m     |
4|                 |
3|     X     X     |
2|                 |
1|                 |
 +-----------------+
   a b c d e f g h""".splitlines()

BASIC_SETUP_LONG = """ +-----------------+
8| r r r r r r r r |
7| d h c e m c h d |
6| . . x . . x . . |
5| . . . . . . . . |
4| . . . . . . . . |
3| . . x . . x . . |
2| D H C M E C H D |
1| R R R R R R R R |
 +-----------------+
   a b c d e f g h  """
BASIC_SETUP_SHORT = "[rrrrrrrrdhcemchd                                DHCMECHDRRRRRRRR]"
BASIC_SETUP_PLACING = (
    'g Ra1 Rb1 Rc1 Rd1 Re1 Rf1 Rg1 Rh1 Cc2 Cf2 Da2 Dh2 Hb2 Hg2 Md2 Ee2',
    's ra8 rb8 rc8 rd8 re8 rf8 rg8 rh8 cc7 cf7 da7 dh7 hb7 hg7 me7 ed7'
    )

CHECK_STEP_POS = """1g
 +-----------------+
8| r r r r r r . r |
7| d h c e . h . d |
6| . C x . . c . . |
5| . . . . m C r . |
4| . . . . E D . . |
3| . . x . . x . R |
2| D H . M . . H . |
1| R R R R R R R . |
 +-----------------+
   a b c d e f g h  """.splitlines()

CHECK_TRAP_STEP = """1g
 +-----------------+
8| r r r r r c . r |
7| d h c e . h M d |
6| . . x . . x . . |
5| . . C . m C r . |
4| . . . . E D . . |
3| . H x . . x . R |
2| D . . . . . H . |
1| R R R R R R R . |
 +-----------------+
   a b c d e f g h  """.splitlines()


class BoardTest(unittest.TestCase):
    def test_get_rnd_step_move(self):
        random.seed(1003)
        move_num, position = board.parse_long_pos(INDUCE_NULL_MOVE_POS)
        for i in range(100):
            position.get_rnd_step_move()

    def test_utility(self):
        self.assertEqual(board.index_to_alg(0), "a1")
        self.assertEqual(board.index_to_alg(7), "h1")
        self.assertEqual(board.index_to_alg(8), "a2")
        self.assertEqual(board.index_to_alg(63), "h8")
        self.assertEqual(board.alg_to_index("a1"), 0)
        self.assertEqual(board.alg_to_index("h1"), 7)
        self.assertEqual(board.alg_to_index("a2"), 8)
        self.assertEqual(board.alg_to_index("h8"), 63)
        for ix in range(64):
            algebraic = board.index_to_alg(ix)
            self.assertEqual(ix, board.alg_to_index(algebraic))
        self.assertEqual(board.index_to_sq(0), (0, 0))
        self.assertEqual(board.index_to_sq(7), (7, 0))
        self.assertEqual(board.index_to_sq(8), (0, 1))
        self.assertEqual(board.index_to_sq(63), (7, 7))
        for ix in range(64):
            column, rank = board.index_to_sq(ix)
            self.assertEqual(ix, board.sq_to_index(column, rank))

    def test_equality(self):
        gb = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        sb = board.Position(board.Color.SILVER, 4, board.BASIC_SETUP)
        self.assertNotEqual(gb, sb)
        self.assertNotEqual(gb, 1)
        b1 = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        modified_setup = list(board.BASIC_SETUP)
        modified_setup[0] ^= 0x0000000000000400
        modified_setup[2] ^= 0x0000000000000400
        b2 = board.Position(board.Color.GOLD, 4, modified_setup)
        self.assertNotEqual(b1, b2)
        b2 = b2.do_move([])
        b1 = b1.do_move_str("Cc2n")
        self.assertEqual(b1, b2)

    def test_sanity_checks(self):
        pos = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        pos.check_hash()
        pos.check_boards()
        bb = list(pos.bitBoards)
        bb[3] ^= 0x400
        pos.bitBoards = tuple(bb)
        self.assertRaises(RuntimeError, pos.check_boards)
        bb[3] ^= 0x400
        bb[2] ^= 0x400
        pos.bitBoards = tuple(bb)
        self.assertRaises(RuntimeError, pos.check_boards)
        self.assertRaises(RuntimeError, pos.check_hash)
        placement = list(pos.placement)
        placement[0] ^= 0x400
        pos.placement = placement
        self.assertRaises(RuntimeError, pos.check_boards)
        placement[1] ^= 0x400
        pos.placement = placement
        self.assertRaises(RuntimeError, pos.check_boards)
        placement[1] ^= 0x400
        pos.placement = placement
        bb[0] ^= 0x400
        pos.bitBoards = tuple(bb)
        pos.check_boards()
        self.assertRaises(RuntimeError, pos.check_hash)
        pos._zhash ^= board.ZOBRIST_KEYS[2][10]
        pos.check_hash()

    def test_end_checks(self):
        pos = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        self.assertEqual(pos.is_goal(), False)
        self.assertEqual(pos.is_rabbit_loss(), False)
        self.assertEqual(pos.is_end_state(), False)
        move, pos = board.parse_long_pos(GOLD_GOAL_POS)
        self.assertEqual(pos.is_goal(), 1)
        self.assertEqual(pos.is_rabbit_loss(), False)
        self.assertEqual(pos.is_end_state(), 1)
        pos = pos.do_move([])
        self.assertEqual(pos.is_goal(), 1)
        self.assertEqual(pos.is_rabbit_loss(), False)
        self.assertEqual(pos.is_end_state(), 1)
        move, pos = board.parse_long_pos(SILVER_GOAL_POS)
        self.assertEqual(pos.is_goal(), -1)
        self.assertEqual(pos.is_rabbit_loss(), False)
        self.assertEqual(pos.is_end_state(), -1)
        pos = pos.do_move([])
        self.assertEqual(pos.is_goal(), -1)
        self.assertEqual(pos.is_rabbit_loss(), False)
        self.assertEqual(pos.is_end_state(), -1)
        move, pos = board.parse_long_pos(DOUBLE_GOAL_POS)
        self.assertEqual(pos.is_goal(), -1)
        self.assertEqual(pos.is_rabbit_loss(), False)
        self.assertEqual(pos.is_end_state(), -1)
        pos = pos.do_move([])
        self.assertEqual(pos.is_goal(), 1)
        self.assertEqual(pos.is_rabbit_loss(), False)
        self.assertEqual(pos.is_end_state(), 1)
        move, pos = board.parse_long_pos(GOLD_RABBIT_LOSS)
        self.assertEqual(pos.is_goal(), False)
        self.assertEqual(pos.is_rabbit_loss(), -1)
        self.assertEqual(pos.is_end_state(), -1)
        pos = pos.do_move([])
        self.assertEqual(pos.is_rabbit_loss(), -1)
        self.assertEqual(pos.is_end_state(), -1)
        move, pos = board.parse_long_pos(SILVER_RABBIT_LOSS)
        self.assertEqual(pos.is_goal(), False)
        self.assertEqual(pos.is_rabbit_loss(), 1)
        self.assertEqual(pos.is_end_state(), 1)
        pos = pos.do_move([])
        self.assertEqual(pos.is_rabbit_loss(), 1)
        self.assertEqual(pos.is_end_state(), 1)
        move, pos = board.parse_long_pos(DOUBLE_RABBIT_LOSS)
        self.assertEqual(pos.is_goal(), False)
        self.assertEqual(pos.is_rabbit_loss(), -1)
        self.assertEqual(pos.is_end_state(), -1)
        pos = pos.do_move([])
        self.assertEqual(pos.is_rabbit_loss(), 1)
        self.assertEqual(pos.is_end_state(), 1)
        move, pos = board.parse_long_pos(DOUBLE_IMMOBILIZATION_POS)
        self.assertEqual(pos.is_goal(), False)
        self.assertEqual(pos.is_rabbit_loss(), False)
        self.assertEqual(pos.is_end_state(), -1)
        pos = pos.do_move([])
        self.assertEqual(pos.is_end_state(), 1)

    def test_parsing(self):
        self.assertRaises(ValueError, board.parse_move, " ")
        directional_move = [(0,8), (8, 9), (9, 1), (1, 0)]
        self.assertEqual(board.parse_move("Ea1n Ea2e Eb2s Eb1w"), directional_move)
        self.assertEqual(board.parse_move("Eb2w Cc3x Ea2n"), [(9, 8), (8, 16)])
        self.assertRaises(ValueError, board.parse_move, "Ed4d")
        self.assertRaises(ValueError, board.parse_move, "Ea1")

        module_pos = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        basic_setup = ["1g"] + BASIC_SETUP_LONG.splitlines()
        parsed_move, parsed_pos = board.parse_long_pos(basic_setup)
        self.assertEqual(parsed_move, 1)
        self.assertEqual(parsed_pos, module_pos)

        module_pos = board.Position(board.Color.SILVER, 4, board.BASIC_SETUP)
        silver_setup = ["Extra", "start", "12s"] + BASIC_SETUP_LONG.splitlines()
        parsed_move, parsed_pos = board.parse_long_pos(silver_setup)
        self.assertEqual(parsed_move, 12)
        self.assertEqual(parsed_pos, module_pos)

        bad_side = ["1f"] + BASIC_SETUP_LONG.splitlines()
        self.assertRaises(ValueError, board.parse_long_pos, bad_side)
        partial_move = ["1g Ra2n"] + BASIC_SETUP_LONG.splitlines()
        self.assertRaises(NotImplementedError, board.parse_long_pos, partial_move)
        extra_separation = ["1g", ""] + BASIC_SETUP_LONG.splitlines()
        self.assertRaises(ValueError, board.parse_long_pos, extra_separation)
        bad_rank = ["1g"] + BASIC_SETUP_LONG.splitlines()
        bad_rank[4] = "5| . . x . . x . . |"
        self.assertRaises(ValueError, board.parse_long_pos, bad_rank)
        bad_piece = ["1g"] + BASIC_SETUP_LONG.splitlines()
        bad_piece[3] = "7| d h c f m c h d |"
        self.assertRaises(ValueError, board.parse_long_pos, bad_piece)

        extra_moves = ["1g"] + BASIC_SETUP_LONG.splitlines()
        extra_moves += [
            "1g Ee2n Md2n", "1s Ed7s Me7s", "# stop parsing", "2g Ee3s"
        ]
        parsed_move, parsed_pos = board.parse_long_pos(extra_moves)
        self.assertEqual(parsed_move, 2)
        self.assertEqual(parsed_pos.color, board.Color.GOLD)
        extra_move_board = [
            "2g",
            " +-----------------+",
            "8| r r r r r r r r |",
            "7| d h c     c h d |",
            "6| . . x e m x . . |",
            "5| . . . . . . . . |",
            "4| . . . . . . . . |",
            "3| . . x M E x . . |",
            "2| D H C     C H D |",
            "1| R R R R R R R R |",
            " +-----------------+",
            "   a b c d e f g h  "
        ]
        extra_move_num, extra_move_pos = board.parse_long_pos(extra_move_board)
        self.assertEqual(parsed_pos, extra_move_pos)

        self.assertRaises(ValueError, board.parse_short_pos, 3, 4, BASIC_SETUP_SHORT)
        self.assertRaises(ValueError, board.parse_short_pos, board.Color.GOLD, 5, BASIC_SETUP_SHORT)
        self.assertRaises(ValueError, board.parse_short_pos, board.Color.GOLD, -1, BASIC_SETUP_SHORT)
        module_pos = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        parsed_pos = board.parse_short_pos(board.Color.GOLD, 4, BASIC_SETUP_SHORT)
        self.assertEqual(parsed_pos, module_pos)
        bad_piece = BASIC_SETUP_SHORT[:15] + "f" + BASIC_SETUP_SHORT[16:]
        short_args = (board.Color.GOLD, 4, bad_piece)
        self.assertRaises(ValueError, board.parse_short_pos, *short_args)

    def test_to_string(self):
        pos = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        self.assertEqual(pos.board_to_str(), BASIC_SETUP_LONG)
        nodots = BASIC_SETUP_LONG.replace(".", " ")
        self.assertEqual(pos.board_to_str(format="long", dots=False), nodots)
        self.assertEqual(pos.board_to_str(format="short"), BASIC_SETUP_SHORT)
        self.assertRaises(ValueError, pos.board_to_str, "invalidformat")
        self.assertEqual(pos.to_placing_move(), BASIC_SETUP_PLACING)
        oldcolor = list(BASIC_SETUP_PLACING)
        oldcolor[0] = 'w' + oldcolor[0][1:]
        oldcolor[1] = 'b' + oldcolor[1][1:]
        oldcolor = tuple(oldcolor)
        self.assertEqual(pos.to_placing_move(old_colors=True), oldcolor)
        self.assertEqual(pos.steps_to_str([(10, 18), (12, 20)]),
                                          "Cc2n Cc3x Ee2n")
        self.assertEqual(pos.steps_to_str([(11, 19), (10, 18), (19, 27)]),
                                          "Md2n Cc2n Md3n Cc3x")
        # try to move empty square
        self.assertRaises(ValueError, pos.steps_to_str, [(18, 19)])
        # make irregular, non-orthogonal step
        self.assertEqual(pos.steps_to_str([(10, 26)]), "Cc2,c4")

    def test_piece_placement(self):
        pos = board.Position(board.Color.GOLD, 4, board.BLANK_BOARD)
        gpos = pos.place_piece(board.Piece.GDOG, 10)
        self.assertRaises(ValueError, gpos.place_piece, board.Piece.GDOG, 10)
        self.assertRaises(ValueError, gpos.remove_piece, 5)
        self.assertEqual(gpos.piece_at(1 << 10), board.Piece.GDOG)
        npos = gpos.remove_piece(10)
        self.assertEqual(pos, npos)
        self.assertEqual(npos.piece_at(1 << 10), board.Piece.EMPTY)
        pos = board.Position(board.Color.SILVER, 4, board.BLANK_BOARD)
        spos = pos.place_piece(board.Piece.SCAMEL, 56)
        self.assertRaises(ValueError, spos.place_piece, board.Piece.GDOG, 56)
        npos = spos.remove_piece(56)
        self.assertEqual(pos, npos)
        self.assertEqual(npos.piece_at(1 << 56), board.Piece.EMPTY)

    def test_check_step(self):
        move, pos = board.parse_long_pos(CHECK_STEP_POS)
        # move from empty square
        result = pos.check_step((16, 24))
        self.assertEqual(bool(result), False)
        self.assertIn("from an empty square", str(result))
        # move to full square
        result = pos.check_step((0, 8))
        self.assertEqual(bool(result), False)
        self.assertIn("to a non-empty square", str(result))
        # move to non-adjacent square
        result = pos.check_step((8, 17))
        self.assertEqual(bool(result), False)
        self.assertIn("to non-adjacent square", str(result))
        # move a frozen piece
        result = pos.check_step((41, 40))
        self.assertEqual(bool(result), False)
        self.assertIn("frozen piece", str(result))
        # move a rabbit backward
        result = pos.check_step((23, 15))
        self.assertEqual(bool(result), False)
        self.assertIn("rabbit back", str(result))
        # start a push
        result = pos.check_step((36, 35))
        self.assertEqual(bool(result), True)
        push_pos = pos.do_step((36, 35))
        # correct finish
        result = push_pos.check_step((28, 36))
        self.assertEqual(bool(result), True)
        # push with weak piece
        result = push_pos.check_step((37, 36))
        self.assertEqual(bool(result), False)
        self.assertIn("too weak", str(result))
        # skip push finish
        result = push_pos.check_step((8, 16))
        self.assertEqual(bool(result), False)
        self.assertIn("neglect finishing", str(result))
        # push another piece while in push
        result = push_pos.check_step((38, 30))
        self.assertEqual(bool(result), False)
        self.assertIn("already in push", str(result))
        # push without anyone to push
        result = pos.check_step((45, 46))
        self.assertEqual(bool(result), False)
        self.assertIn("no pusher", str(result))
        # start push on last step
        ls_pos = pos.do_step((8, 16)).do_step((16, 24)).do_step((24, 32))
        result = ls_pos.check_step((36, 35))
        self.assertEqual(bool(result), False)
        self.assertIn("last step", str(result))

    def test_do_move(self):
        pos = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        fivesteps = [(8, 16), (16, 24), (24, 32), (32, 40), (9, 17)]
        self.assertRaises(board.IllegalMove, pos.do_move, fivesteps)
        jumpstep = [(8, 24), (24, 32)]
        self.assertRaises(board.IllegalMove, pos.do_move, jumpstep)
        pos.do_move(jumpstep, strict_checks=False)
        pos.do_move_str("Da2n Hb2n Cc2n Hb3s Cc3x")
        pos.do_move_str("Hb2n Hb3e Hc3w Hb3s")
        self.assertRaises(board.IllegalMove, pos.do_move_str,
                          "Hb2n Hb3n Hb4n Hb5e Hc5e")
        pos = board.Position(board.Color.GOLD, 4, board.BLANK_BOARD)
        setup = "Ra1 Rb1 Rc1 Rd1 Re1 Rf1 Rg1 Rh1 Da2 Hb2 Cc2 Md2 Ee2 Cf2 Hg2 Dh2"
        pos.do_move_str(setup)
        partial_setup = "Ra1 Rb1 Cc2 Md2 Ee2"
        self.assertRaises(board.IllegalMove, pos.do_move_str, partial_setup)
        pos.do_move_str(partial_setup, strict_checks = False)
        mixed_steps = "Ra1 Rb1 Ra1n"
        self.assertRaises(board.IllegalMove, pos.do_move_str,
                          mixed_steps, strict_checks=False)
        doubled_square = "Ra1 Rb1 Rc1 Ca1"
        self.assertRaises(board.IllegalMove, pos.do_move_str,
                          doubled_square, strict_checks=False)
        opp = "Ra1 Rb1 Rc1 Rd1 Re1 Rf1 Rg1 Rh1 Da2 Hb2 Cc2 Md2 Ee2 Cf2 Hg2 dh2"
        self.assertRaises(board.IllegalMove, pos.do_move_str, opp)
        outside = "Ra1 Rb1 Rc1 Rd1 Re1 Rf1 Rg1 Rh1 Da2 Hb2 Cc2 Md2 Ee3 Cf2 Hg2 Dh2"
        self.assertRaises(board.IllegalMove, pos.do_move_str, outside)
        toomany = "Ra1 Rb1 Rc1 Rd1 Re1 Rf1 Rg1 Rh1 Da2 Hb2 Cc2 Md2 Ee2 Cf2 Hg2 Rh2"
        self.assertRaises(board.IllegalMove, pos.do_move_str, toomany)

    def test_generate_steps(self):
        move, pos = board.parse_long_pos(CHECK_TRAP_STEP)
        single_steps = pos.get_single_steps()
        step_tuples = [s for s, b in single_steps]
        step_tuples.sort()
        expected_single = [
            (1, 9), (2, 10), (3, 11), (4, 12), (5, 13), (6, 7), (8, 9), (8, 16),
            (14, 13), (14, 15), (14, 22), (17, 9), (17, 16), (17, 18), (17, 25),
            (23, 22), (23, 31), (28, 20), (28, 27), (29, 21), (29, 30), (34, 26),
            (34, 33), (34, 35), (34, 42), (37, 45), (54, 46), (54, 62)
        ]
        self.assertEqual(step_tuples, expected_single)
        self.assertEqual(single_steps[0][1].color, board.Color.GOLD)

        pos = board.Position(board.Color.SILVER, 1, board.BASIC_SETUP)
        single_steps = pos.get_single_steps()
        step_tuples = [s for s, b in single_steps]
        step_tuples.sort()
        expected_steps = [
            (48, 40), (49, 41), (50, 42), (51, 43), (52, 44), (53, 45), (54, 46),
            (55, 47)
        ]
        self.assertEqual(step_tuples, expected_steps)
        self.assertEqual(single_steps[0][1].color, board.Color.GOLD)

        move, pos = board.parse_long_pos(CHECK_TRAP_STEP)
        all_steps = pos.get_steps()
        step_tuples = [s for s, b in all_steps]
        step_tuples.sort()
        expected_trap = [
            (1, 9), (2, 10), (3, 11), (4, 12), (5, 13), (6, 7), (8, 9), (8, 16),
            (14, 13), (14, 15), (14, 22), (17, 9), (17, 16), (17, 18), (17, 25),
            (23, 22), (23, 31), (28, 20), (28, 27), (29, 21), (29, 30), (34, 26),
            (34, 33), (34, 35), (34, 42), (36, 35), (36, 44), (37, 45), (38, 30),
            (38, 39), (38, 46), (53, 45), (53, 52), (54, 46), (54, 62), (55, 47)
        ]
        self.assertEqual(step_tuples, expected_trap)
        in_push = pos.do_step((53, 45))
        all_steps = in_push.get_steps()
        self.assertEqual(all_steps[0][0], (54, 53))
        pull_pos = pos.do_step((54, 46))
        all_steps = pull_pos.get_steps()
        step_tuples = [s for s, b in all_steps]
        step_tuples.sort()
        expected_pull = [
            (1, 9), (2, 10), (3, 11), (4, 12), (5, 13), (6, 7), (8, 9), (8, 16),
            (14, 13), (14, 15), (14, 22), (17, 9), (17, 16), (17, 18), (17, 25),
            (23, 22), (23, 31), (28, 20), (28, 27), (29, 21), (29, 30), (34, 26),
            (34, 33), (34, 35), (34, 42), (36, 35), (36, 44), (37, 45), (38, 30),
            (38, 39), (46, 45), (46, 47), (46, 54), (53, 54), (55, 54)
        ]
        self.assertEqual(step_tuples, expected_pull)


    def test_generate_moves(self):
        pos = board.Position(board.Color.GOLD, 4, board.BASIC_SETUP)
        moves = pos.get_moves()
        self.assertEqual(len(moves), 3353)
        moves, nodes = pos.get_moves_nodes()
        self.assertEqual(len(moves), 3353)
        self.assertEqual(nodes, 16440)
