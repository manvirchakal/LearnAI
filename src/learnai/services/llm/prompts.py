"""Jinja2 prompt templates, one file per prompt under ``prompts/*.j2`` — a
prompt change shows up as a reviewable diff instead of being buried inside
a Python f-string.

``autoescape`` is deliberately off: these render to plain text sent to an
LLM, never to HTML, so escaping ``&``/``<``/``>`` would corrupt the prompt.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = Path(__file__).parent / "prompts"


@lru_cache
def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=False,  # noqa: S701 - plain-text LLM prompts, not HTML
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render(template_name: str, **context: object) -> str:
    return _environment().get_template(template_name).render(**context)
