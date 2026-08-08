"""MongoDB connection.

Uses ``pymongo``'s native ``AsyncMongoClient`` rather than Motor — Motor was
deprecated by MongoDB in favor of PyMongo's async API (reached end-of-life
2025-05-14; https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/).
``AsyncMongoClient`` uses asyncio directly instead of delegating to a thread
pool, which is both the supported path and the faster one.

Only this module (and the repositories built on it in Phase 1) may import
``pymongo`` — enforced by the import-linter contract in ``pyproject.toml``.
"""

from __future__ import annotations

from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from learnai.config import Settings

# pymongo's async client/database are generic over the document type. We store
# plain dicts throughout (Pydantic models handle validation at the boundary),
# so every repository in Phase 1 works against this same alias.
MongoClient = AsyncMongoClient[dict[str, Any]]
Database = AsyncDatabase[dict[str, Any]]


def create_mongo_client(settings: Settings) -> MongoClient:
    # pymongo's default serverSelectionTimeoutMS is 30_000 — far too slow for
    # a /health/ready check (or, under an outage, for any request at all) to
    # fail fast on. 5s is generous for a reachable cluster and short enough
    # that health checks and readiness probes behave the way they're meant to.
    return AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5_000)


def get_database(client: MongoClient, settings: Settings) -> Database:
    return client[settings.mongodb_db]


async def ping(client: MongoClient) -> bool:
    try:
        await client.admin.command("ping")
    except Exception:  # noqa: BLE001 — health check: any failure means "not ready"
        return False
    return True
