"""Indexes for ``conversations`` + ``chat_messages`` — Phase 6's chat agent."""

from __future__ import annotations

from learnai.db.mongo import Database

MIGRATION_ID = "0005_chat_indexes"


async def apply(db: Database) -> None:
    # One conversation per (owner, collection) — ConversationRepository.get_or_create's lookup.
    await db["conversations"].create_index([("owner_id", 1), ("collection_id", 1)], unique=True)
    # The seq mechanism's actual uniqueness guarantee: two concurrent appends
    # can never land the same seq in the same conversation — see
    # ConversationRepository.next_seq and ChatMessageRepository.append.
    await db["chat_messages"].create_index(
        [("owner_id", 1), ("conversation_id", 1), ("seq", 1)], unique=True
    )
