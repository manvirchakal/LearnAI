"""Text translation via Claude, cached by ``sha256(text)`` + target
language — the Translate replacement. Claude does better on technical
prose than AWS Translate and preserves LaTeX/Markdown (see
``translation.j2``); the cache is what actually fixes the old design's
pain point of re-translating the same narrative on every request.
"""

from __future__ import annotations

import hashlib

from learnai.config import LLMTask
from learnai.repositories.translations import TranslationRepository
from learnai.services.llm.client import LLMClient
from learnai.services.llm.prompts import render


async def translate_text(
    *, llm: LLMClient, translations: TranslationRepository, text: str, target_language: str
) -> str:
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    cached = await translations.get(text_hash, target_language)
    if cached is not None:
        return cached

    translated = await llm.complete(
        task=LLMTask.translation,
        prompt=render("translation.j2", text=text, target_language=target_language),
    )
    await translations.upsert(text_hash, target_language, translated)
    return translated
