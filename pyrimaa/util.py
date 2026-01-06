# Copyright (c) 2010-2015 Brian Haskin Jr.
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

import re


def _parse_timefield(full_field, start_unit="m"):
    unit_order = " smhd"
    units = {"s": 1, "m": 60, "h": 60 * 60, "d": 60 * 60 * 24}
    num_re = re.compile("[0-9]+")
    units[":"] = units[start_unit]
    seconds = 0
    field = full_field
    if field.startswith(":"):
        field = "0" + field
    nmatch = num_re.match(field)
    while nmatch:
        end = nmatch.end()
        num = int(field[:end])
        if len(field) == end or field[end] == ":":
            sep = start_unit
            start_unit = unit_order[unit_order.find(start_unit) - 1]
        else:
            sep = field[end]
        if sep not in units:
            raise ValueError("Invalid time unit encountered %s" % (sep))
        seconds += num * units[sep]
        if ":" in units:
            del units[":"]
        field = field[end + 1:]
        nmatch = num_re.match(field)
    if field:
        raise ValueError("Invalid time field encountered %s" % (full_field))
    return seconds


def _time_str(seconds):
    units = [("d", 60 * 60 * 24), ("h", 60 * 60), ("m", 60)]
    out = []
    for tag, length in units:
        span = seconds // length
        if span != 0:
            out.append("%s%s" % (int(span), tag))
        seconds -= span * length
    if seconds != 0:
        out.append("%gs" % (seconds, ))
    if len(out) == 0:
        out = ["0"]
    return "".join(out)


field_re = re.compile("[^/]*")


class TimeControl(object):
    def __init__(self, tc_str):
        def _split_tc(tstr):
            fmatch = field_re.match(tc_str)
            if not fmatch:
                f_str = tstr
                rest = ""
            else:
                end = fmatch.end()
                f_str = tstr[:end]
                rest = tstr[end + 1:]
            return (f_str, rest)

        f_str, tc_str = _split_tc(tc_str)
        self.move = _parse_timefield(f_str)
        f_str, tc_str = _split_tc(tc_str)
        if not f_str:
            raise ValueError("Initial reserve time not specified")
        self.reserve = _parse_timefield(f_str)
        f_str, tc_str = _split_tc(tc_str)
        if f_str:
            self.percent = int(f_str)
        else:
            self.percent = 100
        f_str, tc_str = _split_tc(tc_str)
        self.max_reserve = _parse_timefield(f_str)
        f_str, tc_str = _split_tc(tc_str)
        if f_str and f_str[-1] == 't':
            self.turn_limit = int(f_str[:-1])
            self.time_limit = 0
        else:
            self.turn_limit = 0
            self.time_limit = _parse_timefield(f_str, "h")
        self.max_turntime = _parse_timefield(tc_str)

    def __str__(self):
        out = [_time_str(self.move), _time_str(self.reserve)]
        out.append(str(self.percent))
        out.append(_time_str(self.max_reserve))
        if self.turn_limit:
            out.append("%st" % (self.turn_limit, ))
        else:
            out.append(_time_str(self.time_limit))
        out.append(_time_str(self.max_turntime))
        defaults = (None, None, "100", "0", "0", "0")
        while out[-1] == defaults[-1]:
            out = out[:-1]
            defaults = defaults[:-1]
        if out == ["0", "0", "0"]:
            out = ["0", "0", "0", "0"]
        return "/".join(out)
