"""Shared test fixtures."""
import os
import tempfile

# Unique temp file per test session — avoids stale data from previous runs
_TEST_DB = os.path.join(
    tempfile.gettempdir(),
    f"newspulse_test_{os.urandom(4).hex()}.db"
)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
async def client():
    from app.database import init_db
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    from app.database import close_db
    import asyncio
    try:
        asyncio.get_event_loop().run_until_complete(close_db())
    except Exception:
        pass
    for suffix in ("", "-wal", "-shm", "-journal"):
        try:
            os.unlink(_TEST_DB + suffix)
        except (FileNotFoundError, PermissionError):
            pass
