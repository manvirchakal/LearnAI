"""The tutor's search/read tools: output stays within budget and says how to read on."""
import re

import pytest
from langchain.tools import ToolRuntime

from agents import tutor_tools
from agents.tutor_tools import (READ_WINDOW_CHARS, SEARCH_BUDGET_CHARS, TutorContext, read_materials,
                                search_materials)
from services.rag_service import ingest_section, section_text

USER = "tools-user"
WORDS = 3000  # 10 chunks of 300 words


def runtime(file_id=None) -> ToolRuntime:
    return ToolRuntime(state=None, context=TutorContext(USER, file_id), config={}, stream_writer=None,
                       tool_call_id="call-0", store=None)


def search(query, file_id=None, **kwargs) -> str:
    return search_materials.func(query=query, runtime=runtime(file_id), **kwargs)


def read(source, offset=0, file_id=None) -> str:
    return read_materials.func(source=source, offset=offset, runtime=runtime(file_id))


@pytest.fixture(scope="module", autouse=True)
def materials():
    ingest_section(USER, "bio", "ch1", " ".join(f"cell{i}" for i in range(WORDS)))
    ingest_section(USER, "chem", "ch1", " ".join(f"atom{i}" for i in range(WORDS)))


def test_search_places_each_passage_in_its_source():
    out = search("cells", file_id="bio", max_results=2)
    assert out.startswith('2 passages match "cells"')
    full = section_text(USER, "bio", "ch1")
    for source, start, end, total in re.findall(r'source="([^"]+)", characters (\d+)-(\d+) of (\d+)', out):
        assert source == "bio/ch1" and int(total) == len(full)
        assert full[int(start):int(end)] in out  # small enough to show whole


def test_more_results_share_the_same_budget():
    out = search("cells", max_results=8)
    previews = re.split(r'\n\[\d\] source=.*\n', out)[1:]
    assert len(previews) == 8
    assert sum(len(p.split("\n[Preview cut")[0]) for p in previews) <= SEARCH_BUDGET_CHARS
    assert "[Preview cut at" in out


def test_cut_preview_says_where_to_read_on():
    out = search("cells", file_id="bio", max_results=12)
    first = out.split("\n[2]")[0]
    start, = re.search(r"characters (\d+)-", first).groups()
    shown = re.search(r"of \d+\n(.*)\n\[Preview cut", first, re.DOTALL).group(1)
    offset, = re.search(r'read_materials\(source="bio/ch1", offset=(\d+)\)', first).groups()
    assert int(offset) == int(start) + len(shown)

    full = section_text(USER, "bio", "ch1")
    assert full[int(start):].startswith(shown + read("bio/ch1", int(offset)).split("\n")[1])


def test_max_results_is_capped():
    assert f"max_results is capped at {tutor_tools.MAX_SEARCH_RESULTS}" in search("atoms", max_results=50)


def test_reading_windows_cover_the_source_exactly():
    full = section_text(USER, "chem", "ch1")
    text, offset = "", 0
    while True:
        out = read("chem/ch1", offset)
        header, body, footer = out.split("\n")
        assert len(body) <= READ_WINDOW_CHARS
        text += body
        if footer == "[End of source.]":
            break
        offset = int(re.search(r"offset=(\d+)", footer).group(1))
    assert text == full


def test_bad_reads_explain_themselves():
    assert "has" in read("chem/ch1", 10**6) and "characters" in read("chem/ch1", 10**6)
    assert read("chem/nope").startswith('No source "chem/nope"')
    assert read("chem/ch1", file_id="bio").startswith('No source "chem/ch1"')  # outside the chat's file


def test_search_with_nothing_found():
    assert search("anything", file_id="empty").startswith('No passages match "anything"')


def test_search_and_reads_stay_within_listed_sources():
    def scoped(sources):
        return ToolRuntime(state=None, context=TutorContext(USER, sources=sources), config={}, stream_writer=None,
                           tool_call_id="call-0", store=None)

    for sources in (["chem/ch1"], ["chem/ch1", "bio/nothing"]):
        out = search_materials.func(query="atoms", max_results=8, runtime=scoped(sources))
        assert set(re.findall(r'source="([^"]+)"', out)) == {"chem/ch1"}
    assert search_materials.func(query="atoms", runtime=scoped([])).startswith("No passages")
    assert read_materials.func(source="bio/ch1", runtime=scoped(["chem/ch1"])).startswith('No source "bio/ch1"')
    assert read_materials.func(source="chem/ch1", runtime=scoped(["chem/ch1"])).startswith('source="chem/ch1"')
