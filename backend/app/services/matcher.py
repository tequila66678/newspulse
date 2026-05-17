"""Match engine: keyword exact match + embedding semantic similarity."""
import asyncio
import logging

from app.config import settings
from app.database import get_pool

logger = logging.getLogger("newspulse")


async def get_active_subscriptions() -> list[dict]:
    """Get all subscriptions grouped by user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, user_id, keyword, type FROM subscriptions")
    return [dict(r) for r in rows]


def keyword_match(article_title: str, article_summary: str, keyword: str) -> bool:
    """Case-insensitive keyword match in title or summary."""
    kw = keyword.lower()
    text = f"{article_title} {article_summary}".lower()
    return kw in text


_embedding_model = None
_embedding_failed = False


def _get_model():
    """Load embedding model lazily. Returns None if unavailable."""
    global _embedding_model, _embedding_failed
    if _embedding_failed:
        return None
    if _embedding_model is None:
        try:
            import os
            os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "5")
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer("shibing624/text2vec-base-chinese")
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            _embedding_failed = True
            logger.warning(f"Embedding model unavailable, using keyword matching only: {e}")
            return None
    return _embedding_model


def semantic_match(title: str, summary: str, keyword: str, threshold: float | None = None) -> bool:
    """Compute cosine similarity between title+summary and keyword. Returns True if above threshold.
    Returns False if embedding model is unavailable."""
    if threshold is None:
        threshold = settings.embedding_threshold
    model = _get_model()
    if model is None:
        return False
    article_text = f"{title} {summary}"[:512]
    embeddings = model.encode([article_text, keyword])
    similarity = float(embeddings[0] @ embeddings[1].T)
    return similarity >= threshold


async def match_and_notify(article_id: int, title: str, summary: str):
    """Run match engine for a single article, create notifications for matched subscriptions."""
    subs = await get_active_subscriptions()
    if not subs:
        return []

    pool = await get_pool()
    matches = []

    async with pool.acquire() as conn:
        user_tokens = {}
        token_rows = await conn.fetch("SELECT id, fcm_token FROM users WHERE fcm_token IS NOT NULL")
        for r in token_rows:
            user_tokens[r["id"]] = r["fcm_token"]

        for sub in subs:
            matched = False

            if keyword_match(title, summary, sub["keyword"]):
                matched = True
            elif len(sub["keyword"]) >= 2:
                matched = await asyncio.to_thread(semantic_match, title, summary, sub["keyword"])

            if matched:
                await conn.execute(
                    "INSERT INTO notifications (user_id, article_id, type) VALUES ($1, $2, 'track')",
                    sub["user_id"],
                    article_id,
                )
                matches.append({
                    "user_id": sub["user_id"],
                    "fcm_token": user_tokens.get(sub["user_id"]),
                    "keyword": sub["keyword"],
                })

    return matches


async def process_new_articles(article_ids: list[int]):
    """Match all new articles against subscriptions."""
    pool = await get_pool()
    all_matches = []
    async with pool.acquire() as conn:
        for aid in article_ids:
            row = await conn.fetchrow("SELECT id, title, summary FROM articles WHERE id = $1", aid)
            if row:
                matches = await match_and_notify(row["id"], row["title"], row["summary"] or "")
                all_matches.extend(matches)
    return all_matches
