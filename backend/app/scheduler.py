"""Scheduler for periodic tasks using APScheduler."""
import logging
from datetime import date, datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import get_pool
from app.services.aggregator import aggregate
from app.services.matcher import process_new_articles

scheduler = AsyncIOScheduler()
logger = logging.getLogger("newspulse")


async def _fetch_and_match():
    """Fetch news and match against subscriptions."""
    try:
        count = await aggregate()
        match_count = 0
        if count > 0:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT id FROM articles ORDER BY fetched_at DESC LIMIT $1", count
                )
                ids = [r["id"] for r in rows]
            if ids:
                matches = await process_new_articles(ids)
                match_count = len(matches)
                for m in matches:
                    if m.get("fcm_token"):
                        from app.services.push import send_track_push
                        send_track_push(
                            m["fcm_token"],
                            f"追踪命中: {m['keyword']}",
                            "有新的相关新闻",
                            ids[0],
                        )
            logger.info(f"Fetched {count} new articles, {match_count} matches")
    except Exception as e:
        logger.error(f"Fetch-and-match failed: {e}")


async def _generate_daily_digest():
    """Generate and broadcast daily digest."""
    try:
        today = date.today()
        pool = await get_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id FROM daily_digests WHERE date = $1", today
            )
            if existing:
                return

            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            rows = await conn.fetch(
                """SELECT id, title FROM articles
                   WHERE published_at >= $1
                   ORDER BY score DESC LIMIT $2""",
                cutoff,
                settings.digest_count,
            )
            if not rows:
                return

            ids = [r["id"] for r in rows]
            title = rows[0]["title"] if rows else "今日精选"

            digest_row = await conn.fetchrow(
                "INSERT INTO daily_digests (date, article_ids, title) VALUES ($1, $2, $3) RETURNING id",
                today,
                ids,
                title,
            )
            digest_id = digest_row["id"]
            from app.services.push import broadcast_daily_digest
            await broadcast_daily_digest(digest_id, title or "今日精选")
            logger.info(f"Daily digest {digest_id} broadcast")
    except Exception as e:
        logger.error(f"Daily digest failed: {e}")


def start_scheduler():
    scheduler.add_job(
        _fetch_and_match,
        "interval",
        minutes=settings.fetch_interval_minutes,
        id="fetch_and_match",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),  # run immediately on startup
    )
    scheduler.add_job(
        _generate_daily_digest,
        "cron",
        hour=settings.digest_hour,
        minute=0,
        id="daily_digest",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler():
    scheduler.shutdown()
