# Copyright (c) 2010-2014 Brian Haskin Jr.
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

from unittest import TestCase

from pyrimaa.util import TimeControl

class TestTimeControl(TestCase):
    def test_movetime(self):
        self.assertRaises(ValueError, TimeControl, "none")
        tc = TimeControl("30s/1s")
        self.assertEqual(tc.move, 30)
        tc = TimeControl("5m/1s")
        self.assertEqual(tc.move, 300)
        tc = TimeControl("1h/1s")
        self.assertEqual(tc.move, 60*60)
        tc = TimeControl("1d/1s")
        self.assertEqual(tc.move, 60*60*24)
        tc = TimeControl("1:30/1s")
        self.assertEqual(tc.move, 90)

    def test_reservetime(self):
        self.assertRaises(ValueError, TimeControl, "30s")
        tc = TimeControl("30s/10s")
        self.assertEqual(tc.reserve, 10)
        tc = TimeControl("30s/1:30")
        self.assertEqual(tc.reserve, 90)

    def test_percentfill(self):
        tc = TimeControl("30s/10s")
        self.assertEqual(tc.percent, 100)
        tc = TimeControl("30s/10s/100")
        self.assertEqual(tc.percent, 100)
        tc = TimeControl("30s/10s/50")
        self.assertEqual(tc.percent, 50)
        tc = TimeControl("30s/10s/0")
        self.assertEqual(tc.percent, 0)

    def test_max_reserve(self):
        tc = TimeControl("30s/10s")
        self.assertEqual(tc.max_reserve, 0)
        tc = TimeControl("30s/10s/100/0")
        self.assertEqual(tc.max_reserve, 0)
        tc = TimeControl("30s/10s/100/10s")
        self.assertEqual(tc.max_reserve, 10)
        tc = TimeControl("30s/10s/100/1:30")
        self.assertEqual(tc.max_reserve, 90)

    def test_turn_limit(self):
        tc = TimeControl("30s/10s")
        self.assertEqual(tc.turn_limit, 0)
        tc = TimeControl("30s/10s/100/0/0t")
        self.assertEqual(tc.turn_limit, 0)
        tc = TimeControl("30s/10s/100/0/120t")
        self.assertEqual(tc.turn_limit, 120)

    def test_time_limit(self):
        tc = TimeControl("30s/10s")
        self.assertEqual(tc.time_limit, 0)
        tc = TimeControl("30s/10s/100/0/0")
        self.assertEqual(tc.time_limit, 0)
        tc = TimeControl("30s/10s/100/0/1h")
        self.assertEqual(tc.time_limit, 60*60)
        tc = TimeControl("30s/10s/100/0/1:30")
        self.assertEqual(tc.time_limit, 60*90)

    def test_max_turntime(self):
        tc = TimeControl("30s/10s")
        self.assertEqual(tc.max_turntime, 0)
        tc = TimeControl("30s/10s/100/0/0/0")
        self.assertEqual(tc.max_turntime, 0)
        tc = TimeControl("30s/10s/100/0/0/2m")
        self.assertEqual(tc.max_turntime, 120)
        tc = TimeControl("30s/10s/100/0/0/1:30")
        self.assertEqual(tc.max_turntime, 90)

    def test_str(self):
        tc = TimeControl("0/0/0")
        self.assertEqual(str(tc), "0/0/0/0")
        tc = TimeControl("1:30/5/100/0")
        self.assertEqual(str(tc), "1m30s/5m")
        tc = TimeControl("60m/15h/50")
        self.assertEqual(str(tc), "1h/15h/50")
        tc = TimeControl("1/1/100/10/5/5")
        self.assertEqual(str(tc), "1m/1m/100/10m/5h/5m")
        tc = TimeControl("1/1/100/0/50t/5")
        self.assertEqual(str(tc), "1m/1m/100/0/50t/5m")

