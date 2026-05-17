"""Tests for auth endpoints."""
import pytest


@pytest.mark.anyio
async def test_register(client):
    resp = await client.post("/auth/register", json={"email": "test@example.com", "password": "abc123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test@example.com"


@pytest.mark.anyio
async def test_register_duplicate(client):
    await client.post("/auth/register", json={"email": "dup@example.com", "password": "abc123"})
    resp = await client.post("/auth/register", json={"email": "dup@example.com", "password": "abc123"})
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_login(client):
    await client.post("/auth/register", json={"email": "login@example.com", "password": "abc123"})
    resp = await client.post("/auth/login", json={"email": "login@example.com", "password": "abc123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.anyio
async def test_login_wrong_password(client):
    await client.post("/auth/register", json={"email": "wrong@example.com", "password": "abc123"})
    resp = await client.post("/auth/login", json={"email": "wrong@example.com", "password": "wrong"})
    assert resp.status_code == 401
