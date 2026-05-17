"""Tests for push service."""
from app.services.push import _init_firebase


def test_push_module_loads():
    """Module should load without initializing Firebase."""
    from app.services import push
    assert push._initialized is False
