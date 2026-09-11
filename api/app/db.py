"""asyncpg connection pool.

The API connects as `abcd_app`, which holds SELECT and nothing else — there is no
write path to close off at the application layer because the database refuses one.
"""
import logging
from typing import Any, List, Optional

import asyncpg

from .config import get_settings

log = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def connect() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(
            dsn=settings.dsn,
            min_size=settings.pool_min_size,
            max_size=settings.pool_max_size,
            command_timeout=settings.statement_timeout_ms / 1000,
            server_settings={
                "application_name": "abcd-api",
                "statement_timeout": str(settings.statement_timeout_ms),
            },
        )
        log.info("connected to %s:%s/%s", settings.db_host, settings.db_port, settings.db_name)
    return _pool


async def disconnect() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("database pool not initialised")
    return _pool


async def fetch(sql: str, *args: Any) -> List[asyncpg.Record]:
    async with pool().acquire() as conn:
        return await conn.fetch(sql, *args)


async def fetchrow(sql: str, *args: Any) -> Optional[asyncpg.Record]:
    async with pool().acquire() as conn:
        return await conn.fetchrow(sql, *args)


async def fetchval(sql: str, *args: Any) -> Any:
    async with pool().acquire() as conn:
        return await conn.fetchval(sql, *args)
