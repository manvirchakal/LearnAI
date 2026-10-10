"""
Table-of-contents normalization.

Raw TOCs come from two places (the PDF's embedded outline, or the vision model's
parsing of the TOC pages) and have no stable identifiers or end pages. Every
TOC is normalized here into:

    [{"id": "ch1", "number": "Chapter 1", "title": ..., "start_page": 1, "end_page": 30,
      "sections": [{"id": "ch1.s1", "title": ..., "start_page": 1, "end_page": 12}, ...]}]

Section ids are URL-safe and used as storage keys, so titles never end up in
file paths. A chapter without sub-sections gets one section spanning the
chapter, so every chapter is studyable.
"""
from typing import Dict, List, Optional


def toc_from_outline(entries: List[Dict]) -> List[Dict]:
    """Convert PyMuPDF outline entries ({level, title, page}) into raw chapters."""
    chapters: List[Dict] = []
    for entry in entries:
        if entry["level"] == 1:
            chapters.append({
                "number": f"Chapter {len(chapters) + 1}",
                "title": entry["title"].strip(),
                "page": entry["page"],
                "sections": [],
            })
        elif entry["level"] == 2 and chapters:
            chapters[-1]["sections"].append({"title": entry["title"].strip(), "page": entry["page"]})
    return chapters


def _clamp(page: int, num_pages: int) -> int:
    return max(1, min(int(page), num_pages))


def normalize_toc(raw_chapters: List[Dict], num_pages: int) -> List[Dict]:
    """Assign ids and compute inclusive page ranges for chapters and sections."""
    raw_chapters = [c for c in raw_chapters if c.get("title")]
    chapters: List[Dict] = []

    for ci, raw in enumerate(raw_chapters):
        start = _clamp(raw.get("page", 1), num_pages)
        next_start = raw_chapters[ci + 1].get("page") if ci + 1 < len(raw_chapters) else None
        end = _clamp(next_start - 1, num_pages) if next_start else num_pages
        end = max(end, start)

        chapter_id = f"ch{ci + 1}"
        raw_sections = [s for s in raw.get("sections", []) if s.get("title")]
        sections: List[Dict] = []
        for si, sec in enumerate(raw_sections):
            s_start = _clamp(sec.get("page", start), num_pages)
            s_next = raw_sections[si + 1].get("page") if si + 1 < len(raw_sections) else None
            s_end = _clamp(s_next - 1, num_pages) if s_next else end
            sections.append({
                "id": f"{chapter_id}.s{si + 1}",
                "title": sec["title"],
                "start_page": s_start,
                "end_page": max(s_end, s_start),
            })

        if not sections:
            sections = [{"id": f"{chapter_id}.s1", "title": raw["title"], "start_page": start, "end_page": end}]

        chapters.append({
            "id": chapter_id,
            "number": raw.get("number") or f"Chapter {ci + 1}",
            "title": raw["title"],
            "start_page": start,
            "end_page": end,
            "sections": sections,
        })

    return chapters


def single_section_toc(title: str, num_pages: int) -> List[Dict]:
    """Fallback structure for documents without a usable TOC."""
    return normalize_toc([{"number": "Document", "title": title, "page": 1, "sections": []}], num_pages)


def find_section(chapters: List[Dict], section_id: str) -> Optional[Dict]:
    for chapter in chapters:
        for section in chapter["sections"]:
            if section["id"] == section_id:
                return section
    return None


def iter_sections(chapters: List[Dict]):
    for chapter in chapters:
        yield from chapter["sections"]
