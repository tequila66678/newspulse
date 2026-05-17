"""Database connection pool and table initialization.

Supports both PostgreSQL (via asyncpg) and SQLite (via aiosqlite).
Detects dialect from DATABASE_URL scheme.
"""
import re
import logging

import aiosqlite

from app.config import settings

logger = logging.getLogger("newspulse")

_asyncpg_pool = None
_sqlite_conn = None
_dialect = None  # "postgres" or "sqlite"


def _detect_dialect():
    global _dialect
    if _dialect is None:
        url = settings.database_url
        if url.startswith("sqlite"):
            _dialect = "sqlite"
        else:
            _dialect = "postgres"
    return _dialect


# ── SQL translation helpers ────────────────────────────────────────────

_SQL_TRANSLATIONS = [
    (r"\$(\d+)", r"?"),                          # $1, $2 → ?
    (r"::date\b", ""),                           # ::date cast → remove
    (r"\bNOW\(\)\b", "datetime('now')"),          # NOW() → datetime('now')
    (r"\bTRUE\b", "1"),                           # TRUE → 1
    (r"\bFALSE\b", "0"),                          # FALSE → 0
]


def _translate_sql(sql: str) -> str:
    """Translate PG-specific SQL patterns to SQLite-compatible equivalents."""
    for pattern, replacement in _SQL_TRANSLATIONS:
        sql = re.sub(pattern, replacement, sql)
    return sql


def _expand_any(sql: str, args: tuple) -> tuple:
    """Expand = ANY($N) with a list arg into IN (?, ?...).

    Returns (translated_sql, expanded_args).
    """
    match = re.search(r"=\s*ANY\(\$(\d+)\)", sql)
    if match:
        idx = int(match.group(1)) - 1
        if idx < len(args) and isinstance(args[idx], (list, tuple)):
            lst = args[idx]
            if lst:
                placeholders = ", ".join(["?"] * len(lst))
                sql = sql.replace(match.group(0), f"IN ({placeholders})")
                new_args = list(args[:idx]) + list(lst) + list(args[idx + 1 :])
                return sql, tuple(new_args)
            else:
                sql = sql.replace(match.group(0), "IN (NULL)")
                new_args = list(args[:idx]) + list(args[idx + 1 :])
                return sql, tuple(new_args)
    return sql, args


# ── Row wrapper ────────────────────────────────────────────────────────


class _Record:
    """Mimics asyncpg.Record — dict-like access by column name."""

    __slots__ = ("_values", "_mapping")

    def __init__(self, values: tuple, columns: list[str]):
        self._values = values
        self._mapping = {col: i for i, col in enumerate(columns)}

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._mapping[key]]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return self._mapping.keys()

    def values(self):
        return self._values

    def items(self):
        return zip(self._mapping.keys(), self._values)

    def __repr__(self):
        return f"<Record {dict(self.items())}>"


# ── SQLite compat layer ────────────────────────────────────────────────


class _SqliteConnection:
    """Wraps aiosqlite.Connection to match asyncpg.Connection API."""

    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    async def fetchrow(self, sql: str, *args):
        sql, args = _expand_any(sql, args)
        sql = _translate_sql(sql)
        cursor = await self._conn.execute(sql, args)
        row = await cursor.fetchone()
        await self._conn.commit()
        if row is None:
            return None
        return _Record(row, [desc[0] for desc in cursor.description])

    async def fetch(self, sql: str, *args):
        sql, args = _expand_any(sql, args)
        sql = _translate_sql(sql)
        cursor = await self._conn.execute(sql, args)
        rows = await cursor.fetchall()
        await self._conn.commit()
        cols = [desc[0] for desc in cursor.description]
        return [_Record(r, cols) for r in rows]

    async def execute(self, sql: str, *args):
        sql, args = _expand_any(sql, args)
        sql = _translate_sql(sql)
        await self._conn.execute(sql, args)
        await self._conn.commit()


class _SqliteAcquireCtx:
    """Async context manager returned by pool.acquire()."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn = None

    async def __aenter__(self):
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        return _SqliteConnection(self._conn)

    async def __aexit__(self, *args):
        if self._conn:
            await self._conn.close()


class _SqlitePool:
    """Minimal pool-like interface matching asyncpg.Pool for SQLite."""

    def __init__(self, db_path: str):
        self._db_path = db_path

    def acquire(self):
        return _SqliteAcquireCtx(self._db_path)

    async def close(self):
        pass  # SQLite connections are closed per-acquire


# ── Public API ─────────────────────────────────────────────────────────


async def get_pool():
    """Return a database pool (PostgreSQL) or pool-like wrapper (SQLite)."""
    dialect = _detect_dialect()
    global _asyncpg_pool, _sqlite_conn

    if dialect == "sqlite":
        # SQLite: no real pooling needed, return a lightweight wrapper
        # Strip sqlite:/// prefix to get file path
        db_path = settings.database_url
        for prefix in ("sqlite:///", "sqlite://", "sqlite:"):
            if db_path.startswith(prefix):
                db_path = db_path[len(prefix) :]
                break
        if not db_path:
            db_path = "./newspulse.db"
        return _SqlitePool(db_path)

    # PostgreSQL: use asyncpg
    import asyncpg

    if _asyncpg_pool is None:
        _asyncpg_pool = await asyncpg.create_pool(
            settings.database_url, min_size=2, max_size=10
        )
    return _asyncpg_pool


async def init_db():
    """Create tables if they don't exist."""
    dialect = _detect_dialect()

    if dialect == "sqlite":
        db_path = settings.database_url
        for prefix in ("sqlite:///", "sqlite://", "sqlite:"):
            if db_path.startswith(prefix):
                db_path = db_path[len(prefix) :]
                break
        if not db_path:
            db_path = "./newspulse.db"

        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.executescript(_SQLITE_DDL)
            await conn.commit()
    else:
        import asyncpg

        p = await get_pool()
        async with p.acquire() as conn:
            await conn.execute(_PG_DDL)


async def close_db():
    """Close database connections."""
    global _asyncpg_pool, _sqlite_conn, _dialect
    _dialect = None
    if _asyncpg_pool:
        await _asyncpg_pool.close()
        _asyncpg_pool = None
    if _sqlite_conn:
        await _sqlite_conn.close()
        _sqlite_conn = None


# ── DDL Statements ─────────────────────────────────────────────────────

_PG_DDL = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        fcm_token VARCHAR(512),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS subscriptions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        keyword VARCHAR(255) NOT NULL,
        type VARCHAR(20) NOT NULL DEFAULT 'topic',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS articles (
        id SERIAL PRIMARY KEY,
        title VARCHAR(1024) NOT NULL,
        summary TEXT,
        source VARCHAR(255) NOT NULL,
        source_url VARCHAR(2048) UNIQUE,
        published_at TIMESTAMPTZ,
        fetched_at TIMESTAMPTZ DEFAULT NOW(),
        score FLOAT DEFAULT 0.0,
        embedding BYTEA
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
        type VARCHAR(20) NOT NULL DEFAULT 'track',
        sent_at TIMESTAMPTZ DEFAULT NOW(),
        read BOOLEAN DEFAULT FALSE
    );

    CREATE TABLE IF NOT EXISTS daily_digests (
        id SERIAL PRIMARY KEY,
        date DATE UNIQUE NOT NULL,
        article_ids JSONB DEFAULT '[]',
        title VARCHAR(512),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC);
    CREATE INDEX IF NOT EXISTS idx_articles_score ON articles(score DESC);
    CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
    CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, sent_at DESC);
"""

_SQLITE_DDL = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        fcm_token TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        keyword TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'topic',
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        summary TEXT,
        source TEXT NOT NULL,
        source_url TEXT UNIQUE,
        published_at TEXT,
        fetched_at TEXT DEFAULT (datetime('now')),
        score REAL DEFAULT 0.0,
        embedding BLOB
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
        type TEXT NOT NULL DEFAULT 'track',
        sent_at TEXT DEFAULT (datetime('now')),
        read INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS daily_digests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL,
        article_ids TEXT DEFAULT '[]',
        title TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC);
    CREATE INDEX IF NOT EXISTS idx_articles_score ON articles(score DESC);
    CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
    CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, sent_at DESC);
"""
