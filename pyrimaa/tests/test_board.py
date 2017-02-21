import unittest

import pyrimaa.board as board

Color = board.Color
Piece = board.Piece
Position = board.Position

class PositionTest(unittest.TestCase):
    def test_contruction(self):
        '''should create an empty position'''
        empty_pos = board.Position(Color.GOLD, 4, board.BLANK_BOARD)
        self.assertEqual(empty_pos.color, Color.GOLD)
        self.assertEqual(empty_pos.stepsLeft, 4)
        self.assertEqual(empty_pos.inpush, False)
        self.assertEqual(empty_pos.last_from, None)
        self.assertEqual(empty_pos.bitBoards, board.BLANK_BOARD)


class BoardTest(unittest.TestCase):
    def test_parse_short_pos(self):
        '''should create a board from a short string'''
        short_str = \
            "[r    rrrrrch md MeRR    R d    R    E  R    h D   HC H   R      ]"
        pos = board.parse_short_pos(Color.GOLD, 4, short_str)
        self.assertEqual(pos.color, Color.GOLD)
        self.assertEqual(pos.stepsLeft, (1 << 2))
        self.assertEqual(pos.inpush, False)
        self.assertEqual(pos.bitBoards[Piece.SRABBIT] & (1<<(7*8)), (1<<(7*8)))
        self.assertEqual(pos.bitBoards[Piece.GRABBIT] & (1<<(7*8)), 0)
        self.assertEqual(pos.bitBoards[Piece.SRABBIT] & (1<<1), 0)
        self.assertEqual(pos.bitBoards[Piece.GRABBIT] & (1<<1), 1<<1)
        self.assertEqual(pos.last_from, None)
        self.assertEqual(pos._to_short_str(), short_str)
    
    def test_parse_pos(self):
        long_str = "\n13g\n" \
                   " +-----------------+\n" \
                   "8| r r r r r r r r |\n" \
                   "7| d . c m . h . d |\n" \
                   "6| . h x . . x c . |\n" \
                   "5| . . . . E e . . |\n" \
                   "4| . . . . . . . . |\n" \
                   "3| . H x M . x H D |\n" \
                   "2| R R C . . C . . |\n" \
                   "1| D . R R R R R R |\n" \
                   " +-----------------+\n" \
                   "   a b c d e f g h  "
        (movenumber, pos) = board.parse_long_pos(long_str)
        self.assertEqual(movenumber, 13)
        self.assertEqual(pos.bitBoards[Piece.SDOG], (1<<(6*8+0))|(1<<(6*8+7)));
        self.assertEqual(pos.bitBoards[Piece.GELEPHANT], (1<<(4*8+4)))
        self.assertEqual(pos.bitBoards[Piece.SELEPHANT], (1<<(4*8+5)))
        self.assertEqual(pos.bitBoards[Piece.SCAMEL], (1<<(6*8+3)))
        self.assertEqual(pos.color, Color.GOLD)
        self.assertEqual(pos.inpush, False)
        self.assertEqual(pos.stepsLeft, 4)
        self.assertEqual(pos.last_from, None)
        self.assertEqual(pos._to_long_str(), long_str[5:])

