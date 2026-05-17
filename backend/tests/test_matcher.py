"""Tests for match engine."""
from app.services.matcher import keyword_match


def test_keyword_match_in_title():
    assert keyword_match("马斯克收购Twitter", "", "马斯克") is True


def test_keyword_match_case_insensitive():
    assert keyword_match("Elon Musk launches rocket", "", "elon musk") is True


def test_keyword_no_match():
    assert keyword_match("OpenAI发布新模型", "", "马斯克") is False


def test_keyword_partial_no_match():
    assert keyword_match("太空探索取得新进展", "", "太空探索技术公司") is False
