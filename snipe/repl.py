# -*- encoding: utf-8 -*-
# Copyright © 2017 the Snipe contributors
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following
# disclaimer in the documentation and/or other materials provided
# with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
# THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.


'''
snipe.repl
------------

Editor subclass for a python REPL
'''


import bisect
import sys
import unittest.mock as mock

from . import editor
from . import interactive
from . import keymap
from . import util


OUTPUT_START = 'OUTPUT_START'
OUTPUT_END = 'OUTPUT_END'


class REPL(editor.Editor):
    def __init__(self, *args, **kw):
        kw.setdefault('name', 'REPL')
        super().__init__(*args, **kw)

        # YYY
        import _sitebuiltins  # type:ignore
        _sitebuiltins._Printer.MAXLINES = 99999999999999999

        if 'REPL' not in self.buf.state:
            self.state = {}
            self.buf.state['REPL'] = self.state
            self.state['high_water_mark'] = self.buf.mark(0)
            self.state['stakes'] = []
            self.state['in'] = []
            self.state['out'] = []
            self.state['ps1'] = '>>> '
            self.output(util.SPLASH)
            cprt = (
                'Type "help", "copyright", "credits" or "license" for more'
                ' information.')
            self.output("Python (snipe) %s on %s\n%s\n" % (
                sys.version, sys.platform, cprt))
            self.output(self.state['ps1'], prop={'mutable': False})
            self.state['environment'] = {
                'context': self.context,
                'window': self,
                'In': self.state['in'],
                'Out': self.state['out'],
                }
        else:
            self.state = self.buf.state['REPL']

    def title(self):
        return super().title() + ' [%d]' % len(self.state['in'])

    def output(self, s, prop=None):
        if (self.state['stakes']
                and self.state['stakes'][-1][0].point == len(self.buf)
                and self.state['stakes'][-1][1] == OUTPUT_END):
            del self.state['stakes'][-1]
        else:
            self.state['stakes'].append(
                (self.buf.mark(len(self.buf)), OUTPUT_START))
        self.state['high_water_mark'].point = len(self.buf)
        if prop is None:
            self.state['high_water_mark'].insert(s)
        else:
            self.state['high_water_mark'].insert(s, prop)
        self.cursor.point = self.state['high_water_mark']
        self.state['stakes'].append((self.buf.mark(len(self.buf)), OUTPUT_END))

    def brackets(self, mark):
        x = bisect.bisect(self.state['stakes'], (mark, 'ZZZ'))
        if x >= len(self.state['stakes']):
            return self.state['stakes'][-1], (None, None)
        else:
            # there shouldn't ever be less than two stakes because we run
            # output in __init__
            assert len(self.state['stakes']) > 1
            assert x > 0
            return tuple(self.state['stakes'][x - 1:x + 1])

    def writable(self, count, where=None):
        if not super().writable(count, where):
            return False
        # XXX should find the size of the operation before okaying it
        return self.brackets(self.cursor)[0][1] == OUTPUT_END

    def go_eval(self):
        input = self.buf[self.state['high_water_mark']:]
        ((left_mark, left_sigil), (right_mark, right_sigil)) = \
            self.brackets(self.cursor)
        save = ''
        if (self.cursor.point < self.state['high_water_mark']
                and left_sigil == OUTPUT_END):
            save = input
            input = self.buf[left_mark:right_mark.point - 1]
            self.cursor.point = self.state['high_water_mark']
            self.cursor.point += self.replace(len(save), input)
        with self.save_excursion():
            self.end_of_buffer()
            self.insert('\n')
            self.redisplay()
            self.undo()

        result_val = None

        their_displayhook = sys.displayhook

        def my_displayhook(val):
            nonlocal result_val
            result_val = val
            return their_displayhook(val)

        # YYY whoever is running the last eval gets the credit
        self.state['environment']['window'] = self

        with mock.patch('sys.displayhook', my_displayhook):
            result = util.eval_output(input, self.state['environment'])

        if result is not None:
            self.state['in'].append(input)
            self.state['out'].append(result_val)
            self.cursor.point = len(self.buf)
            self.cursor.insert('\n')
            self.output(result)
            self.output(self.state['ps1'], prop={'mutable': False})
        # possiby incomplete from uphistory
        self.cursor.replace(0, save)
        return result is not None

    @keymap.bind('Control-M')
    def go2(self):
        if not self.go_eval():
            self.insert('\n')

    @keymap.bind('Control-C Control-C', 'Control-J')
    def go(self):
        if not self.go_eval():
            self.context.message('incomplete input')

    @keymap.bind('Control-A', '[home]')
    def electric_beginning_of_line(
            self,
            count: interactive.integer_argument=None,
            interactive: interactive.isinteractive=False,
            ):
        point = self.cursor.point
        mark, sigil = self.brackets(self.cursor)[0]
        self.beginning_of_line(count, interactive)
        if not interactive or count is not None:
            return

        if sigil == OUTPUT_END and self.cursor.point < mark < point:
            self.cursor.point = mark
