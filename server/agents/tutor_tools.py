"""
Tools the tutor agent calls to look things up in the student's materials.

Every response is capped in code, whatever the model asks for, so a lookup
can't flood its context:
    search_materials  the best passages for a query; their text shares
                      SEARCH_BUDGET_CHARS, so more results means shorter previews
    read_materials    READ_WINDOW_CHARS of one source from an offset, to read on
                      from (or before) a passage
Each response says where its text sits in the source and how to read further,
so the model needs no instructions beyond the tool descriptions.
"""
from dataclasses import dataclass
from typing import List, Optional

from langchain.tools import ToolRuntime, tool

from services.rag_service import parse_source, search_passages, section_text, source_id

SEARCH_BUDGET_CHARS = 6000
MAX_SEARCH_RESULTS = 8
READ_WINDOW_CHARS = 4000


@dataclass
class TutorContext:
    """Whose materials the tools see, and which: one file (a book), else the listed
    sources (a collection's), else all of them."""
    user_id: str
    file_id: Optional[str] = None
    sources: Optional[List[str]] = None

    def allows(self, source: str) -> bool:
        if self.file_id:
            return source.partition("/")[0] == self.file_id
        return self.sources is None or source in self.sources


def _cut(text: str, start: int, limit: int) -> int:
    """End of a window of at most limit characters from start, at a word break if one is near."""
    end = start + limit
    if end >= len(text):
        return len(text)
    space = text.rfind(" ", start + limit // 2, end)
    return space if space != -1 else end


def _read_on(source: str, offset: int, length: int) -> str:
    if offset >= length:
        return "[End of source.]"
    return f'[Continues: read_materials(source="{source}", offset={offset})]'


@tool
def search_materials(query: str, runtime: ToolRuntime[TutorContext], max_results: int = 3) -> str:
    """Search the student's study materials for passages relevant to a query, best match first."""
    context = runtime.context
    count = max(1, min(max_results, MAX_SEARCH_RESULTS))
    passages = search_passages(context.user_id, query, top_k=count, file_id=context.file_id,
                               sources=context.sources)
    if not passages:
        return f'No passages match "{query}" in the student\'s materials.'

    budget = SEARCH_BUDGET_CHARS // len(passages)
    lines = [f'{len(passages)} passages match "{query}", best first. Positions are characters in each source.']
    if max_results > MAX_SEARCH_RESULTS:
        lines[0] += f" (max_results is capped at {MAX_SEARCH_RESULTS}.)"
    for n, p in enumerate(passages, 1):
        source = source_id(p.file_id, p.section)
        shown = _cut(p.text, 0, budget)
        lines.append(f'\n[{n}] source="{source}", characters {p.start}-{p.start + len(p.text)} '
                     f"of {p.source_length}")
        lines.append(p.text[:shown])
        if shown < len(p.text):
            lines.append(f"[Preview cut at {shown} of {len(p.text)} characters. "
                         + _read_on(source, p.start + shown, p.source_length)[1:])
    return "\n".join(lines)


@tool
def read_materials(source: str, runtime: ToolRuntime[TutorContext], offset: int = 0) -> str:
    """Read a source from the student's materials, starting at a character offset."""
    context = runtime.context
    parsed = parse_source(source)
    if not parsed or not context.allows(source):
        return f'No source "{source}" in these materials. Use a source from search_materials results.'
    text = section_text(context.user_id, *parsed)
    if text is None:
        return f'No source "{source}" in these materials. Use a source from search_materials results.'
    if not 0 <= offset < len(text):
        return f'offset {offset} is outside source "{source}", which has {len(text)} characters (0-{len(text) - 1}).'

    end = _cut(text, offset, READ_WINDOW_CHARS)
    return (f'source="{source}", characters {offset}-{end} of {len(text)}\n'
            f"{text[offset:end]}\n{_read_on(source, end, len(text))}")


TUTOR_TOOLS = [search_materials, read_materials]
