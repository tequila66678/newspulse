"""Database connection pool and table initialization."""
import asyncpg
from app.config import settings

pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    return pool


async def init_db():
    """Create tables if they don't exist."""
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("""
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
        """)


async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None
