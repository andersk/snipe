# -*- encoding: utf-8 -*-
# Copyright © 2014 the Snipe contributors
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
snipe.util
----------

Assorted utility functions.
'''


import sys
import os
import logging
import asyncio
import functools
import contextlib
import time
import datetime
import math
import json

import aiohttp

from . import _websocket


class SnipeException(Exception):
    pass


class Configurable:
    registry = {}

    def __init__(
        self, key,
        default=None, doc=None, action=None, coerce=None, validate=None,
        string=None, oneof=None,
        ):
        self.key = key
        self.default = default
        self._action = action
        self._validate = validate
        self._coerce = coerce
        self._string = string
        self.oneof = oneof
        if oneof and not validate:
            self._validate = val_oneof(oneof)
        self.override = None
        self.doc = doc
        self.registry[key] = self

    def __get__(self, instance, owner):
        if not instance:
            return self
        if self.override is not None:
            return self.override
        if not instance.context:
            return self.default
        return instance.context.conf.get('set', {}).get(self.key, self.default)

    def __set__(self, instance, v):
        value = self.coerce(v)
        if not self.validate(value):
            raise TypeError('%s invalid for %s' % (repr(v), self.key))
        instance.context.conf.setdefault('set', {})[self.key] = value
        self.override = None
        self.action(instance.context, value)

    def set_override(self, v):
        value = self.coerce(v)
        if not self.validate(value):
            raise TypeError('%s invalid for %s' % (repr(v), self.key))
        self.override = value

    def action(self, instance, value):
        if self._action is not None:
            self._action(instance.context, value)

    def coerce(self, value):
        if self._coerce is not None:
            return self._coerce(value)
        return value

    def validate(self, value):
        if self._validate is not None:
            return self._validate(value)
        return True

    def string(self, value):
        if self._string is not None:
            return self._string(value)
        return str(value)

    @classmethod
    def immanentize(self, context):
        for configurable in self.registry.values():
            configurable.action(context, configurable.__get__(context, self))

    @classmethod
    def set(self, instance, key, value):
        obj = self.registry[key]
        obj.__set__(instance, value)

    @classmethod
    def get(self, instance, key):
        obj = self.registry[key]
        return obj.__get__(instance, None)

    @classmethod
    def set_overrides(self, overrides):
        for k,v in overrides.items():
            self.registry[k].set_override(v)


def coerce_bool(x):
    if hasattr(x, 'lower'):
        return x.lower().strip() in ('true', 'on', 'yes')
    else:
        return bool(x)


class Level(Configurable):
    def __init__(self, key, logger, default=logging.WARNING, doc=None):
        super().__init__(key, default, doc=doc)
        self.logger = logger

    def action(self, instance, value):
        logging.getLogger(self.logger).setLevel(value)

    names = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']

    def coerce(self, value):
        if hasattr(value, 'upper'): # stringish
            v = value.strip().upper()
            if v in self.names:
                return getattr(logging, v)
            try:
                return int(value)
            except ValueError:
                pass
        return value

    def validate(self, value):
        return isinstance(value, int) and value >= 0


# these don't need to actually be properties anywhere
for userspace_name, program_name in [
    ('log.context', 'Snipe'),
    ('log.roost.engine', 'Rooster'),
    ('log.roost', 'Roost'),
    ('log.ttyfrontend', 'TTYFrontend'),
    ('log.ttyrender', 'TTYRender'),
    ('log.curses', 'TTYRender.curses'),
    ('log.messager', 'Messager'),
    ('log.editor', 'Editor'),
    ('log.asyncio', 'asyncio'),
    ('log.gapbuffer', 'GapBuffer'),
    ('log.backend.terminus', 'TerminusBackend'),
    ('log.backend.startup', 'StartupBackend'),
    ('log.filter', 'filter'),
    ('log.websocket', 'WebSocket'),
    ]:
    Level(
        userspace_name,
        program_name,
        {'log.context': logging.INFO}.get(userspace_name, logging.WARNING),
        'logging for %s object' % (program_name,)
        )


LICENSE = '''
Copyright © 2014 the Snipe contributors
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

1. Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above
copyright notice, this list of conditions and the following
disclaimer in the documentation and/or other materials provided
with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.
'''


SPLASH = '''
Welcome to snipe.

  snipe is a messaging client (and editor) written by Karl Ramm.

  You can type ? for help at this screen, but on some screens you'll
  need to press the escape key first.   If you're new here, there should
  be a cheatsheet for commonly used keys at the top of the window.

  snipe is free/open source software.  Type ? L for relevant lawyerese.
'''

USER_AGENT = 'snipe 0 (development) (python %s) (aiohttp %s)' % (
    sys.version.split('\n')[0].strip(), aiohttp.__version__)


def coro_cleanup(f):
    @asyncio.coroutine
    @functools.wraps(f)
    def catch_and_log(*args, **kw):
        try:
            return (yield from asyncio.coroutine(f)(*args, **kw))
        except asyncio.CancelledError:
            pass #yay
        except Exception:
            if args and hasattr(args[0], 'log'):
                log = args[0].log
            else:
                log = logging.getLogger('coro_cleanup')
            log.exception('coroutine cleanup')
    return catch_and_log


@contextlib.contextmanager
def stopwatch(tag, log=None):
    if log is None:
        log = logging.getLogger('stopwatch')
    t0 = time.time()
    yield
    log.debug('%s took %fs', tag, time.time() - t0)


def listify(f):
    '''Decorator that turns a function that returns an iterator into a function
    that returns a list; because generators are a convenient idiom but
    sometimes you really want lists.
    '''
    @functools.wraps(f)
    def listifier(*args, **kw):
        return list(f(*args, **kw))
    return listifier


def timestr(t):
    if t is None:
        return '[not]'

    try:
        t = float(t)
    except:
        return '[?' + repr(t) + ']'

    try:
        return '[' + datetime.datetime.fromtimestamp(t).isoformat(' ') + ']'
    except OverflowError:
        pass

    if t < 0:
        if math.isinf(t):
            return '[immemorial]'
        else:
            return '[undefined]'
    else:
        if math.isinf(t):
            return '[omega]'
        else:
            return '[unknown]'

    return '[impossible]'


class JSONDecodeError(SnipeException):
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return str(self.data)


class HTTP_JSONmixin:
    # object must have a .log attribute
    @asyncio.coroutine
    def http_json(
            self, method, url,
            data=None, params=None, headers=None, compress=None, auth=None,
            ):
        self.log.debug(
            'http_json(%s, %s, %s, %s, %s, %s)',
            repr(method), repr(url), repr(data), repr(params), repr(headers), repr(compress))

        if headers is None:
            headers = {}

        send_headers = {
            'User-Agent': USER_AGENT,
        }

        kwargs = {}
        if auth is not None:
            kwargs['auth'] = auth

        if data is not None:
            data = data.encode('UTF-8')
            headers['Content-Length'] = str(len(data))
        send_headers.update(headers)

        response = yield from aiohttp.request(
            method, url,
            data=data, params=params, compress=compress, headers=headers,
            **kwargs)

        result = []
        while True:
            data = yield from response.content.read()
            if data == b'':
                break
            result.append(data)

        response.close()

        result = b''.join(result)
        try:
            result = result.decode('utf-8')
        except UnicodeError as e:
            self.log.error(
                'json decode failure from %s on %s', url, repr(result))
            raise JSONDecodeError(repr(result)) from e
        try:
            result = json.loads(result)
        except ValueError as e:
            self.log.error(
                'json parse failure from %s on %s', url, repr(result))
            raise JSONDecodeError(result) from e
        return result


class JSONWebSocket:
    def __init__(self, log):
        self.resp = None
        self.url = None
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.resp is not None:
            self.resp.close()
            self.resp = None
        return False

    @asyncio.coroutine
    def connect(self, url, headers=None):
        if headers is None:
            headers = {}
        headers['User-Agent'] = USER_AGENT
        self.url = url
        self.log.debug('connecting to %s %s', url, headers)
        self.reader, self.writer, self.resp = yield from _websocket.websocket(
            url, headers)

        return self.resp

    def write(self, data):
        assert self.resp is not None
        return self.writer.send(json.dumps(data))

    @asyncio.coroutine
    def read(self):
        assert self.resp is not None

        while True:
            message = yield from self.reader.read()

            if message.tp == aiohttp.websocket.MSG_PING:
                self.writer.pong()
            elif message.tp == aiohttp.websocket.MSG_CLOSE:
                break
            elif message.tp == aiohttp.websocket.MSG_BINARY:
                self.log.error(
                    'Unknown binary message: %s', repr(message))
            elif message.tp == aiohttp.websocket.MSG_TEXT:
                try:
                    m = json.loads(message.data)
                except:
                    self.log.exception('Decoding json: %s', repr(message.data))
                    continue
                return m
            else:
                self.log.error('Unknown websocket message type')


@contextlib.contextmanager
def safe_write(path, mode=0o600):
    """Open a file for writing without letting go with both hands."""
    directory, name = os.path.split(path)
    tmp = os.path.join(directory, ',' + name)
    backup = os.path.join(directory, name + '~')

    opener = lambda file, flags: os.open(file, flags, mode=mode)
    fp = open(tmp, 'w', opener=opener)

    yield fp

    fp.close()
    # TODO consider checking that the size of the file matches what was written

    if os.path.exists(path):
        with contextlib.suppress(OSError):
            os.unlink(backup)
        os.link(path, backup)
    os.rename(tmp, path)


def eval_output(string, environment, mode='single'):
    import code
    import io
    import traceback

    try:
        if mode == 'exec':
            c = compile(string, '<input>', mode)
        else:
            c = code.compile_command(string, symbol=mode)
        if c is None:
            return None
        else:
            sio = io.StringIO()
            with contextlib.redirect_stdout(sio):
                eval(c, environment)
            out = sio.getvalue()
    except:
        out = traceback.format_exc()

    return out

def val_oneof(vals):
    return lambda x: x in vals
