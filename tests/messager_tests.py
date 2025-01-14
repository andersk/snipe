#!/usr/bin/python3
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
Unit tests for messager module
'''

import contextlib
import datetime
import io
import math
import os
import unittest

from unittest.mock import (patch)

import mocks

import snipe.chunks as chunks
import snipe.filters as filters
import snipe.imbroglio as imbroglio
import snipe.messager as messager
import snipe.util as util


class TestMessager(unittest.TestCase):
    def test_0(self):
        fe = mocks.FE()
        w = messager.Messager(fe)
        self.assertEqual(
            [[({'visible', 'bar'}, '\n')]],
            [chunk.tagsets() for (mark, chunk) in w.view(0)])
        w.renderer = mocks.Renderer()
        f = filters.Yes()
        fe.context.conf['rule'] = [('yes', {'foreground': 'green'})]
        x = messager.Messager(fe, prototype=w, filter_new=f)
        self.assertEqual(
            [[({'visible', 'bar'}, '\n')]],
            [chunk.tagsets() for (mark, chunk) in w.view(0)])
        self.assertIs(x.filter, f)
        self.assertEqual(len(x.rules), len(fe.context.conf['rule']))

    def test_focus(self):
        w = messager.Messager(mocks.FE())
        c = w.cursor
        w.secondary, w.cursor = c, None
        self.assertTrue(w.focus())
        self.assertIs(w.cursor, c)
        self.assertIsNone(w.secondary)

    def test_view_bad_message(self):
        f = mocks.FE()
        w = messager.Messager(f)
        f.context.backends._messages[0]._display = [()]  # malformed chunk
        w.search_term = 'foo'
        self.assertEqual(
            ({'visible', 'bar'}, '[()]\n'),
            [chunk.tagsets() for (mark, chunk) in w.view(0)][0][0])

    def test_find(self):
        f = mocks.FE()
        w = messager.Messager(f)
        self.assertFalse(w.find('foo', True))
        self.assertEqual(
            [[({'visible', 'bar'}, '\n')]],
            [chunk.tagsets() for (mark, chunk) in w.view(0)])
        f.context.backends._messages.append(mocks.Message())
        f.context.backends._messages[-1]._display = chunks.Chunk(
            [((), 'foo\n')])
        self.assertEqual(
            [[({'visible', 'bar'}, '\n')], [((), 'foo\n')]],
            [chunk.tagsets() for (mark, chunk) in w.view(0)])
        self.assertTrue(w.find('foo', True))
        self.assertEqual(
            [[((), '\n')], [({'visible', 'bar'}, 'foo\n')]],
            [chunk.tagsets() for (mark, chunk) in w.view(0)])

    def test_check_redisplay_hint(self):
        f = mocks.FE()
        w = messager.Messager(f)
        w.renderer = mocks.Renderer()
        self.assertFalse(w.check_redisplay_hint({}))
        hint = w.redisplay_hint()
        self.assertTrue(w.check_redisplay_hint(hint))
        r = (
            f.context.backends._messages[0],
            f.context.backends._messages[-1])
        self.assertFalse(w.check_redisplay_hint({'messages': r}))
        w.filter = filters.Yes()
        w.renderer = mocks.Renderer(range=r)
        self.assertTrue(w.check_redisplay_hint({'messages': r}))

    def test_after_command(self):
        f = mocks.FE()
        w = messager.Messager(f)
        m = mocks.Message()
        m.omega = True
        f.context.backends._messages.append(m)
        w.next_message()
        w.after_command()
        self.assertEqual(
            f.context.starks[-1], f.context.backends._messages[0].time)

    def test_modeline(self):
        f = mocks.FE()
        w = messager.Messager(f)
        w.renderer = mocks.Renderer()
        self.assertEqual(
            w.modeline(), ([(set(), 'filter default')], [({'right'}, '1')]))
        m = f.context.backends._messages[0]
        m.time = 0.0
        w.renderer = mocks.Renderer((m, m))
        os.environ['TZ'] = 'GMT'
        self.assertEqual(
            w.modeline(), (
                [({'dim'}, '1970-01-01 00:00'), (set(), ' filter default')],
                [({'right'}, '1')]))
        m.time = float('NaN')

        class mockdatetime(datetime.datetime):
            @staticmethod
            def now():
                return datetime.datetime.fromtimestamp(60)

        with patch('datetime.datetime', mockdatetime):
            self.assertEqual(
                w.modeline(), (
                    [({'dim'}, '00:01'), (set(), ' filter default')],
                    [({'right'}, '1')]))

    def test_move_cleverness_arg(self):
        f = mocks.FE()
        w = messager.Messager(f)
        w.move_cleverly(True, None)
        self.assertEqual(w.move_cleverly_state, 0)
        w.move_cleverly(True, 1)
        self.assertEqual(w.move_cleverly_state, 1)
        w.move_cleverly(True, 'xx')
        self.assertEqual(w.move_cleverly_state, 2)

    def test_move(self):
        f = mocks.FE()
        w = messager.Messager(f)
        f.context.backends._messages.append(mocks.Message())

        self.assertIs(w.cursor, f.context.backends._messages[0])
        w.next_message()
        self.assertIs(w.cursor, f.context.backends._messages[1])
        w.prev_message()
        self.assertIs(w.cursor, f.context.backends._messages[0])
        w.move(0)
        self.assertIs(w.cursor, f.context.backends._messages[0])

    def test_move_cleverly(self):
        f = mocks.FE()
        w = messager.Messager(f)
        f.context.backends._messages.append(mocks.Message())

        self.assertIs(w.cursor, f.context.backends._messages[0])
        w.next_message_cleverly()
        self.assertIs(w.cursor, f.context.backends._messages[1])
        w.prev_message_cleverly()
        self.assertIs(w.cursor, f.context.backends._messages[0])

    def test_move_backwards_target(self):
        f = mocks.FE()
        w = messager.Messager(f)
        w.move(-1)
        self.assertIsNotNone(f.context.backends._target)
        self.assertLess(f.context.backends._target, 0)
        self.assertTrue(math.isinf(f.context.backends._target))

    def test_cursor_set_walk(self):
        f = mocks.FE()
        w = messager.Messager(f)
        m = mocks.Message()
        m.omega = True
        f.context.backends._messages.append(m)
        self.assertEqual(w.cursor, f.context.backends._messages[0])
        w.cursor_set_walk_mark(None, False)
        self.assertEqual(w.cursor, f.context.backends._messages[1])

    def test_end_beginning(self):
        f = mocks.FE()
        w = messager.Messager(f)
        m = mocks.Message()
        m.omega = True
        f.context.backends._messages.append(m)
        self.assertEqual(w.cursor, f.context.backends._messages[0])
        w.end()
        self.assertEqual(w.cursor, f.context.backends._messages[1])
        w.beginning()
        self.assertEqual(w.cursor, f.context.backends._messages[0])

    @imbroglio.test
    async def test_filter_slot(self):
        f = mocks.FE()
        w = messager.Messager(f)
        it = w.filter_slot(key='0', keyseq='0', arg=None)
        self.assertRaises(util.SnipeException, lambda: it.send(None))
        f.context.conf['filter'] = {'_0': 'yes'}
        self.assertEqual(str(w.filter), 'filter default')
        it = w.filter_slot(key='0', keyseq='0', arg=None)
        self.assertRaises(StopIteration, lambda: it.send(None))
        self.assertEqual(str(w.filter), 'filter default and yes')
        _called = None

        async def mock_filter_edit_name(*args, **kw):
            nonlocal _called
            _called = (args, kw)

        w.filter_edit_name = mock_filter_edit_name

        await w.filter_slot(key='0', keyseq='0', arg=[4])

        self.assertEqual(_called, (('_0',), {}))

    def test_filter_everything(self):
        f = mocks.FE()
        w = messager.Messager(f)
        w.filter_everything()
        self.assertEqual(str(w.filter), 'no')

    def test_filter_clear_decorate(self):
        f = mocks.FE()
        w = messager.Messager(f)
        w.filter = filters.Yes()
        decor = {'foreground': 'white', 'background': 'blue'}
        w.filter_clear_decorate(decor)
        self.assertEqual(f.context.conf['rule'], [('yes', decor)])
        self.assertEqual(
            [[({'visible', 'bar'}, '\n')]],
            [chunk.tagsets() for (mark, chunk) in w.view(0)])

    def test_filter_personals(self):
        f = mocks.FE()
        w = messager.Messager(f)
        w.filter_personals()
        self.assertEqual(str(w.filter), 'filter default and personal')

    def test_filter_cleverly_negative(self):
        f = mocks.FE()
        w = messager.Messager(f)
        w.filter_cleverly_negative()
        self.assertEqual(str(w.filter), 'filter default and not yes')

    @imbroglio.test
    async def test_send(self):
        f = mocks.FE()
        m = mocks.Message()
        m.omega = True
        f.context.backends._messages.append(m)
        w = messager.Messager(f)
        w.renderer = mocks.Renderer((
            f.context.backends._messages[0],
            f.context.backends._messages[-1]))

        c = w.cursor

        _read_args = None
        _read_kw = None
        _read_result = 'foo\nbar'

        async def read_string(*args, **kw):
            nonlocal _read_args, _read_kw
            _read_args, _read_kw = args, kw
            return _read_result

        w.read_string = read_string
        await w.send()

        self.assertEqual(f.context.backends._sent[-1], ('foo', 'bar'))
        self.assertNotIn('modes', _read_kw)
        self.assertEqual(w.secondary, c)

        w.cursor = c
        _read_result = 'foo'

        await w.send(msg=c)

        self.assertIn('modes', _read_kw)
        self.assertEqual(f.context.backends._sent[-1], ('foo', ''))

    def test_quit_hook_starks(self):
        f = mocks.FE()
        w = messager.Messager(f)
        self.assertIsNotNone(w.replymsg())
        self.assertFalse(f.context.starks)
        w.quit_hook()
        self.assertTrue(f.context.starks)

    def test_match(self):
        f = mocks.FE()
        w = messager.Messager(f)
        self.assertFalse(w.match('foo'))
        f.context.backends._messages[0]._display = chunks.Chunk(
            [((), 'foo\n')])
        self.assertTrue(w.match('foo'))

    def test_pageup_backfill(self):
        f = mocks.FE()
        w = messager.Messager(f)
        w.renderer = mocks.Renderer(
            range=tuple(f.context.backends._messages * 2))
        self.assertIsNone(f.context.backends._target)
        w.pageup()
        self.assertTrue(math.isinf(f.context.backends._target))

    def test_replymsg_none(self):
        f = mocks.FE()
        w = messager.Messager(f)
        f.context.backends._messages[0].omega = True
        self.assertIsNone(w.replymsg())

    @imbroglio.test
    async def test_followup_and_reply(self):
        f = mocks.FE()
        w = messager.Messager(f)

        recipient = None

        async def mock_send(to, *args, **kw):
            nonlocal recipient
            recipient = to

        w.send = mock_send

        await w.followup()

        self.assertEqual(recipient, 'followup')

        await w.reply()

        self.assertEqual(recipient, 'reply')

    @imbroglio.test
    async def test_filter_edit(self):
        f = mocks.FE()
        w = messager.Messager(f)

        filter = 'no and no and no and yes'
        w.read_string = returning(filter)

        await w.filter_edit()

        self.assertEqual(str(w.filter), filter)

        w.read_oneof = returning('name')
        await w.filter_edit([4])

        self.assertEqual(f.context.conf['filter']['name'], filter)

        w.read_string = returning('')

        await w.filter_edit([4])

        self.assertTrue('name' not in f.context.conf['filter'])

    @imbroglio.test
    async def test_filter_color_rules(self):
        f = mocks.FE()
        w = messager.Messager(f)
        w.read_string = returning('green')
        w.filter = filters.Yes()

        await w.filter_foreground_background()

        self.assertEqual(
            f.context.conf['rule'],
            [('yes', {'foreground': 'green', 'background': 'green'})])

        w.filter = filters.Yes()
        await w.filter_foreground()
        self.assertEqual(
            f.context.conf['rule'],
            [('yes', {'foreground': 'green'})])

        w.filter = filters.Yes()
        await w.filter_background()
        self.assertEqual(
            f.context.conf['rule'],
            [('yes', {'background': 'green'})])

        w.read_string = returning('messager_tests.TestMessager')
        w.filter = filters.Yes()
        await w.filter_decor()
        self.assertEqual(
            f.context.conf['rule'],
            [('yes', {'decor': 'messager_tests.TestMessager'})])

        w.read_string = returning('nonexistent.object')
        w.filter = filters.Yes()
        with self.assertRaises(util.SnipeException):
            await w.filter_decor()

    def test_filter_push(self):
        f = mocks.FE()
        w = messager.Messager(f)
        w.filter = None
        f0 = filters.Yes()
        w.filter_push(f0)
        self.assertIs(w.filter, f0)
        self.assertEqual(w.filter_stack, [])
        f1 = filters.No()
        w.filter_push(f1)
        self.assertEqual(w.filter, filters.And(f0, f1))
        self.assertEqual(w.filter_stack, [f0])

    @imbroglio.test
    async def test_filter_class(self):
        f = mocks.FE()
        w = messager.Messager(f)
        w.read_string = returning('green')

        await w.filter_class()

        self.assertEqual(
            str(w.filter),
            'filter default and backend == "roost" and class = "green"')

    @imbroglio.test
    async def test_filter_sender(self):
        f = mocks.FE()
        w = messager.Messager(f)
        w.read_string = returning('green')

        await w.filter_sender()

        self.assertEqual(
            str(w.filter),
            'filter default and sender = "green"')

    def test_filter_cleverly_and_pop(self):
        f = mocks.FE()
        w = messager.Messager(f)

        w.filter_cleverly()

        self.assertEqual(str(w.filter), 'filter default and yes')

        w.filter_pop()
        self.assertEqual(str(w.filter), 'filter default')

        w.filter = filters.Yes()
        self.assertEqual(str(w.filter), 'yes')

        w.filter_pop()
        self.assertEqual(str(w.filter), 'filter default')

    @imbroglio.test
    async def test_filter_save(self):
        f = mocks.FE()
        w = messager.Messager(f)

        self.assertEqual(w.default_filter, 'filter default')

        F1 = 'flig == "quoz"'
        w.filter = filters.makefilter(F1)

        await w.filter_save(True)

        self.assertEqual(w.default_filter, F1)

        F2 = 'flig'
        w.filter = filters.makefilter(F2)
        w.read_oneof = returning('quoz')
        await w.filter_save()

        self.assertEqual(f.context.conf['filter']['quoz'], F2)

    def test_show_message_data(self):
        f = mocks.FE()
        w = messager.Messager(f)

        string = None

        def mock_show(s):
            nonlocal string
            string = s

        w.show = mock_show

        w.show_message_data()

        self.assertEqual(string, '''<mocks.Message>
not personal, not outgoing, not noise, not omega, not error
sender: "None"
body: ""

{}''')

    def test_goto_time(self):
        f = mocks.FE()
        w = messager.Messager(f)

        os.environ['TZ'] = 'GMT'
        target = None

        def mock_cswm(*args):
            nonlocal target
            target = args

        w.cursor_set_walk_mark = mock_cswm

        w.goto_time(0)

        self.assertEqual(target, (0, True, 0))

    @imbroglio.test
    async def test_goto(self):
        f = mocks.FE()
        w = messager.Messager(f)

        os.environ['TZ'] = 'GMT'
        target = None

        def mock_goto_time(*args):
            nonlocal target
            target = args

        w.goto_time = mock_goto_time

        w.read_string = returning('1970-01-01 00:00:00')

        await w.goto()

        self.assertEqual(target, (0.0,))

    def test_next_prev_day(self):
        f = mocks.FE()
        w = messager.Messager(f)

        target = None

        def mock_goto_time(*args):
            nonlocal target
            target = args
        w.goto_time = mock_goto_time

        class MockDate:
            TODAY = datetime.date(1970, 1, 1)

            @classmethod
            def today(klass, *args):
                return klass.TODAY

        f.context.backends._messages[0].omega = True
        os.environ['TZ'] = 'GMT'
        try:
            # pypy
            with patch('datetime.date.today', MockDate.today):
                w.prev_day()
        except TypeError:
            # cpython
            with patch('datetime.date', MockDate):
                w.prev_day()
        self.assertEqual(target, (0.0,))

        f.context.backends._messages[0].omega = False
        f.context.backends._messages[0].time = \
            datetime.datetime(1970, 1, 2).timestamp()
        target = None
        w.prev_day()
        self.assertEqual(target, (0.0,))

        target = None
        w.next_day(-1)
        self.assertEqual(target, (0.0,))

        target = None
        f.context.backends._messages[0].omega = True
        w.next_day()
        self.assertIsNone(target)

        f.context.backends._messages[0].omega = False
        f.context.backends._messages[0].time = \
            datetime.datetime(1969, 12, 31).timestamp()
        w.next_day()
        self.assertEqual(target, (0.0,))

        target = None
        w.prev_day(-1)
        self.assertEqual(target, (0.0,))

    def test_mark(self):
        f = mocks.FE()
        w = messager.Messager(f)
        self.assertIsNone(w.the_mark)
        m = f.context.backends._messages
        m.append(mocks.Message())
        m.append(mocks.Message())
        w.set_mark()
        self.assertEqual(w.the_mark, w.cursor)
        w.set_mark(m[-1])
        self.assertEqual(w.the_mark, m[-1])
        self.assertEqual(w.mark_ring[-1], m[0])

        where = w.cursor
        there = w.the_mark
        anywhere = w.mark_ring[-1]
        w.set_mark(prefix=[4])
        self.assertEqual(w.mark_ring[0], where)
        self.assertEqual(w.the_mark, anywhere)
        self.assertEqual(w.cursor, there)

        o = object()
        self.assertIs(o, w.make_mark(o))  # pass through

        self.assertNotEqual(w.cursor, m[0])
        w.go_mark(m[0])
        self.assertEqual(w.cursor, m[0])
        w.the_mark = m[-1]
        w.exchange_point_and_mark()
        self.assertEqual(w.cursor, m[-1])
        self.assertEqual(w.the_mark, m[0])

    def test_move_starks(self):
        w = messager.Messager(mocks.FE())
        m = w.context.backends._messages
        m.append(mocks.Message())
        m.append(mocks.Message())
        self.assertEqual(w.cursor, m[0])
        w.end()
        self.assertEqual(w.cursor, m[-1])
        w.previous_stark()
        self.assertEqual(w.cursor, m[-1])
        w.beginning()
        self.assertEqual(w.cursor, m[0])
        w.context.starks = [m[0].time, m[2].time]
        w.next_stark()
        self.assertEqual(w.cursor, m[2])
        w.previous_stark()
        self.assertEqual(w.cursor, m[0])
        w.next_stark()
        m.append(mocks.Message())
        w.next_stark()
        self.assertEqual(w.cursor, m[3])

    def test_rot13(self):
        w = messager.Messager(mocks.FE())
        m0 = w.context.backends._messages[0]
        m0.body = 'abjurer'
        w.rot13()
        self.assertEqual(m0.body, 'nowhere')

    def test_list_destinations(self):
        w = messager.Messager(mocks.FE())
        out = None

        def mock_show(text):
            nonlocal out
            out = text

        w.show = mock_show
        w.list_destinations()
        self.assertEqual(out, '')

    @imbroglio.test
    async def test_write_region(self):
        w = messager.Messager(mocks.FE())
        w.context.backends._messages[0].body = 'foo'
        w.context.backends._messages.append(mocks.Message())
        fp = io.StringIO('')
        w.read_filename = returning('/nope')

        @contextlib.contextmanager
        def mock_open(*args):
            print(args)
            yield fp

        messager.open = mock_open
        await w.write_region()
        del messager.open
        self.assertEqual(fp.getvalue(), 'foo')

    def test_set_stark(self):
        w = messager.Messager(mocks.FE())
        m = w.context.backends._messages

        self.assertFalse(w.context.starks)
        m[0].omega = True
        w.set_stark()
        self.assertFalse(w.context.starks)
        m[0].omega = False
        w.set_stark()
        self.assertEqual(w.context.starks, [m[0].time])


def returning(s):
    async def mocked(*args, **kw):
        return s
    return mocked


if __name__ == '__main__':
    unittest.main()
