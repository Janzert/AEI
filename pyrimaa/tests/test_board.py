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


class BoardTest(unittest.TestCase):
    def test_get_rnd_step_move(self):
        random.seed(1003)
        move_num, position = board.parse_long_pos(INDUCE_NULL_MOVE_POS)
        for i in range(100):
            position.get_rnd_step_move()

