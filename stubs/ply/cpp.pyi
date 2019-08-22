# Stubs for ply.cpp (Python 3)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from typing import Any, Optional

STRING_TYPES: Any
STRING_TYPES = str
xrange = range
tokens: Any
literals: str

def t_CPP_WS(t: Any): ...

t_CPP_POUND: str
t_CPP_DPOUND: str
t_CPP_ID: str

def CPP_INTEGER(t: Any): ...
t_CPP_INTEGER = CPP_INTEGER
t_CPP_FLOAT: str

def t_CPP_STRING(t: Any): ...
def t_CPP_CHAR(t: Any): ...
def t_CPP_COMMENT1(t: Any): ...
def t_CPP_COMMENT2(t: Any): ...
def t_error(t: Any): ...
def trigraph(input: Any): ...

class Macro:
    name: Any = ...
    value: Any = ...
    arglist: Any = ...
    variadic: Any = ...
    vararg: Any = ...
    source: Any = ...
    def __init__(self, name: Any, value: Any, arglist: Optional[Any] = ..., variadic: bool = ...) -> None: ...

class Preprocessor:
    lexer: Any = ...
    macros: Any = ...
    path: Any = ...
    temp_path: Any = ...
    parser: Any = ...
    def __init__(self, lexer: Optional[Any] = ...) -> None: ...
    def tokenize(self, text: Any): ...
    def error(self, file: Any, line: Any, msg: Any) -> None: ...
    t_ID: Any = ...
    t_INTEGER: Any = ...
    t_INTEGER_TYPE: Any = ...
    t_STRING: Any = ...
    t_SPACE: Any = ...
    t_NEWLINE: Any = ...
    t_WS: Any = ...
    def lexprobe(self) -> None: ...
    def add_path(self, path: Any) -> None: ...
    def group_lines(self, input: Any) -> None: ...
    def tokenstrip(self, tokens: Any): ...
    def collect_args(self, tokenlist: Any): ...
    def macro_prescan(self, macro: Any): ...
    def macro_expand_args(self, macro: Any, args: Any): ...
    def expand_macros(self, tokens: Any, expanded: Optional[Any] = ...): ...
    def evalexpr(self, tokens: Any): ...
    source: Any = ...
    def parsegen(self, input: Any, source: Optional[Any] = ...) -> None: ...
    def include(self, tokens: Any) -> None: ...
    def define(self, tokens: Any) -> None: ...
    def undef(self, tokens: Any) -> None: ...
    ignore: Any = ...
    def parse(self, input: Any, source: Optional[Any] = ..., ignore: Any = ...) -> None: ...
    def token(self): ...