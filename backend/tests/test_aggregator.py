"""Tests for news aggregator."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.aggregator import _estimate_score, _clean_html


def test_clean_html():
    assert _clean_html("<p>Hello <b>World</b></p>") == "Hello World"


def test_estimate_score_urgency():
    article = {"title": "Breaking: major event", "source": {"name": "Reuters"}}
    score = _estimate_score(article)
    assert score >= 0.6


def test_estimate_score_low():
    article = {"title": "Some random news", "source": {"name": "Unknown Blog"}}
    score = _estimate_score(article)
    assert 0.2 <= score <= 0.5


@pytest.mark.asyncio
async def test_aggregate_empty_when_no_api_key():
    import app.config
    old_key = app.config.settings.newsapi_key
    old_rss = app.config.settings.supported_rss_urls
    app.config.settings.newsapi_key = ""
    app.config.settings.supported_rss_urls = []

    # Mock the database pool to avoid needing a real PostgreSQL connection
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.execute = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    with patch("app.services.aggregator.get_pool", AsyncMock(return_value=mock_pool)):
        from app.services.aggregator import aggregate
        count = await aggregate()

    app.config.settings.newsapi_key = old_key
    app.config.settings.supported_rss_urls = old_rss
    assert count == 0
