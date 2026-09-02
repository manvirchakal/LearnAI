from __future__ import annotations

import hashlib

from bson import ObjectId

from learnai.config import LLMTask
from learnai.repositories.translations import TranslationRepository
from learnai.services.translation import translate_text
from tests.fakes.llm import FakeLLMClient
from tests.fakes.mongo import FakeAsyncDatabase


async def test_cache_miss_translates_and_caches() -> None:
    db = FakeAsyncDatabase()
    translations = TranslationRepository(db, ObjectId())  # type: ignore[arg-type]
    llm = FakeLLMClient(completions={LLMTask.translation: "Bonjour le monde"})

    result = await translate_text(
        llm=llm, translations=translations, text="Hello world", target_language="fr-FR"
    )

    assert result == "Bonjour le monde"
    assert llm.calls[0]["task"] == LLMTask.translation

    text_hash = hashlib.sha256(b"Hello world").hexdigest()
    assert await translations.get(text_hash, "fr-FR") == "Bonjour le monde"


async def test_cache_hit_skips_translation() -> None:
    db = FakeAsyncDatabase()
    translations = TranslationRepository(db, ObjectId())  # type: ignore[arg-type]

    await translate_text(
        llm=FakeLLMClient(completions={LLMTask.translation: "Bonjour le monde"}),
        translations=translations,
        text="Hello world",
        target_language="fr-FR",
    )

    broken_llm = FakeLLMClient()
    result = await translate_text(
        llm=broken_llm, translations=translations, text="Hello world", target_language="fr-FR"
    )

    assert result == "Bonjour le monde"
    assert broken_llm.calls == []


async def test_different_target_language_is_a_different_cache_entry() -> None:
    db = FakeAsyncDatabase()
    translations = TranslationRepository(db, ObjectId())  # type: ignore[arg-type]

    await translate_text(
        llm=FakeLLMClient(completions={LLMTask.translation: "Bonjour le monde"}),
        translations=translations,
        text="Hello world",
        target_language="fr-FR",
    )

    llm = FakeLLMClient(completions={LLMTask.translation: "Hallo Welt"})
    result = await translate_text(
        llm=llm, translations=translations, text="Hello world", target_language="de-DE"
    )

    assert result == "Hallo Welt"
    assert llm.calls  # actually called, not served from the fr-FR cache entry


async def test_translations_are_owner_scoped() -> None:
    db = FakeAsyncDatabase()
    owner_a, owner_b = ObjectId(), ObjectId()
    translations_a = TranslationRepository(db, owner_a)  # type: ignore[arg-type]
    translations_b = TranslationRepository(db, owner_b)  # type: ignore[arg-type]

    await translate_text(
        llm=FakeLLMClient(completions={LLMTask.translation: "Bonjour le monde"}),
        translations=translations_a,
        text="Hello world",
        target_language="fr-FR",
    )

    text_hash = hashlib.sha256(b"Hello world").hexdigest()
    assert await translations_b.get(text_hash, "fr-FR") is None
