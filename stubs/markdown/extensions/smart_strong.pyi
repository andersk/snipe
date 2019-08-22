# Stubs for markdown.extensions.smart_strong (Python 3)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from . import Extension
from ..inlinepatterns import SimpleTagPattern
from typing import Any

SMART_STRONG_RE: str
STRONG_RE: str

class SmartEmphasisExtension(Extension):
    def extendMarkdown(self, md: Any, md_globals: Any) -> None: ...

def makeExtension(*args: Any, **kwargs: Any): ...