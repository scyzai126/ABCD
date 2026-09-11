import sys
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db, facets  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    """A client bound to a freshly-created pool.

    asyncpg connections belong to the event loop that created them, and pytest-asyncio
    gives each test its own loop, so the pool is built and torn down per test rather
    than shared. These are contract tests against the live container -- the numbers
    they assert were read out of the actual dump.
    """
    await db.connect()
    facets.clear_cache()
    await facets.get(refresh=True)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test/api/v1") as c:
            yield c
    finally:
        await db.disconnect()
        facets.clear_cache()
