"""News aggregation: fetch from NewsAPI + RSS sources, dedup, score, and store."""
import hashlib
import logging
import re

import feedparser
import httpx

from app.config import settings
from app.database import get_pool

logger = logging.getLogger("newspulse")


async def fetch_newsapi() -> list[dict]:
    """Fetch top headlines from NewsAPI free tier."""
    if not settings.newsapi_key:
        return []
    url = "https://newsapi.org/v2/top-headlines"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params={"apiKey": settings.newsapi_key, "language": "zh", "pageSize": 50})
        if resp.status_code != 200:
            return []
        data = resp.json()
        return [
            {
                "title": a["title"],
                "summary": a.get("description") or "",
                "source": a["source"]["name"],
                "source_url": a["url"],
                "published_at": a.get("publishedAt"),
                "score": _estimate_score(a),
            }
            for a in data.get("articles", [])
            if a.get("title")
        ]


async def fetch_rss(url: str) -> list[dict]:
    """Fetch articles from an RSS feed."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=30)
        if resp.status_code != 200:
            return []
    feed = feedparser.parse(resp.text)
    articles = []
    for entry in feed.entries[:30]:
        title = entry.get("title", "")
        summary = entry.get("summary", entry.get("description", ""))
        articles.append({
            "title": title,
            "summary": summary,
            "source": feed.feed.get("title", url),
            "source_url": entry.get("link", ""),
            "published_at": _parse_date(entry),
            "score": _estimate_score_rss(title, summary, feed.feed.get("title", url)),
        })
    return articles


def _estimate_score(article: dict) -> float:
    """Heuristic score from source weight + keyword bonuses."""
    score = 0.3
    high_impact_sources = ["BBC", "Reuters", "AP", "Al Jazeera", "新华社", "CNN", "央视", "人民日报", "联合早报"]
    source_name = article.get("source", {}).get("name", "") if isinstance(article.get("source"), dict) else ""
    for kw in high_impact_sources:
        if kw in str(source_name):
            score += 0.3
            break
    title = str(article.get("title", ""))
    summary = str(article.get("description", article.get("summary", "")))
    text = f"{title} {summary}".lower()

    # Military / conflict keywords
    military_kw = ["war", "missile", "nuclear", "invasion", "sanctions", "strike", "military",
                   "战争", "导弹", "核", "入侵", "制裁", "空袭", "军事", "冲突", "武器"]
    for kw in military_kw:
        if kw in text:
            score += 0.3
            break

    # Political / geopolitical keywords
    political_kw = ["president", "election", "coup", "treaty", "summit", "diplomatic",
                    "总统", "选举", "政变", "条约", "峰会", "外交", "国会", "白宫", "克里姆林宫"]
    for kw in political_kw:
        if kw in text:
            score += 0.25
            break

    # Breakthrough / discovery keywords
    breakthrough_kw = ["breakthrough", "first-ever", "discovered", "revolutionary", "unprecedented",
                       "突破", "首次", "发现", "重大发现", "革命性", "历史性"]
    for kw in breakthrough_kw:
        if kw in text:
            score += 0.25
            break

    # Urgency keywords
    urgency_keywords = ["突发", "快讯", "紧急", "重磅", "breaking", "just in", "alert"]
    for kw in urgency_keywords:
        if kw in title.lower():
            score += 0.2
            break
    return min(score, 1.0)


def _parse_date(entry) -> str | None:
    """Extract published date from RSS entry."""
    for attr in ("published", "updated", "created"):
        val = entry.get(attr)
        if val:
            return val
    return None


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _estimate_score_rss(title: str, summary: str, source: str) -> float:
    """Score RSS article based on keyword relevance to world events."""
    score = 0.3
    # High-impact source bonus
    high_impact = ["BBC", "联合早报", "Science Daily", "澎湃", "Reuters", "AP", "Al Jazeera"]
    for kw in high_impact:
        if kw.lower() in source.lower():
            score += 0.3
            break

    text = f"{title} {summary}".lower()

    # Military / conflict
    for kw in ["war", "missile", "nuclear", "invasion", "sanctions", "strike", "military",
               "战争", "导弹", "核", "入侵", "制裁", "空袭", "军事", "冲突"]:
        if kw in text:
            score += 0.3
            break

    # Political / geopolitical
    for kw in ["president", "election", "coup", "treaty", "summit", "diplomatic",
               "总统", "选举", "政变", "条约", "峰会", "外交", "白宫"]:
        if kw in text:
            score += 0.25
            break

    # Breakthrough / discovery
    for kw in ["breakthrough", "first-ever", "discovered", "revolutionary",
               "突破", "首次", "发现", "重大发现", "革命性"]:
        if kw in text:
            score += 0.25
            break

    # Urgency
    for kw in ["突发", "快讯", "紧急", "重磅", "breaking", "alert"]:
        if kw in text:
            score += 0.2
            break

    return min(score, 1.0)


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)[:2000]


async def aggregate():
    """Pull from all sources, deduplicate, store new articles. Returns count of new articles."""
    raw = []

    try:
        newsapi_articles = await fetch_newsapi()
        raw.extend(newsapi_articles)
    except Exception as e:
        logger.warning(f"NewsAPI fetch failed: {e}")

    for rss_url in settings.supported_rss_urls:
        try:
            rss_articles = await fetch_rss(rss_url)
            raw.extend(rss_articles)
            logger.info(f"RSS {rss_url}: {len(rss_articles)} articles")
        except Exception as e:
            logger.warning(f"RSS {rss_url} failed: {e}")

    pool = await get_pool()
    new_count = 0

    async with pool.acquire() as conn:
        for art in raw:
            url = art.get("source_url", "")
            if not url:
                continue
            existing = await conn.fetchrow(
                "SELECT id FROM articles WHERE source_url = $1", url
            )
            if existing:
                continue

            await conn.execute(
                """INSERT INTO articles (title, summary, source, source_url, published_at, score)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                _clean_html(art.get("title", "")[:1024]),
                _clean_html(art.get("summary", "")[:2000]),
                art.get("source", "unknown")[:255],
                url,
                art.get("published_at"),
                art.get("score", 0.3),
            )
            new_count += 1

    return new_count
