"""Tests for the finger server."""

import json
import os
import time
import tempfile
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


@pytest.fixture
def plans_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        old = os.environ.get("FINGER_PLANS_DIR")
        os.environ["FINGER_PLANS_DIR"] = tmpdir
        yield Path(tmpdir)
        if old:
            os.environ["FINGER_PLANS_DIR"] = old
        else:
            os.environ.pop("FINGER_PLANS_DIR", None)


@pytest.fixture
def auth_dir():
    """Configure auth to use a temp directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_key = os.environ.get("FINGER_KEYS_PATH")
        old_token = os.environ.get("FINGER_TOKEN_DIR")
        os.environ["FINGER_KEYS_PATH"] = str(Path(tmpdir) / "keys.json")
        os.environ["FINGER_TOKEN_DIR"] = str(Path(tmpdir) / "tokens")
        yield Path(tmpdir)
        if old_key:
            os.environ["FINGER_KEYS_PATH"] = old_key
        else:
            os.environ.pop("FINGER_KEYS_PATH", None)
        if old_token:
            os.environ["FINGER_TOKEN_DIR"] = old_token
        else:
            os.environ.pop("FINGER_TOKEN_DIR", None)


@pytest.fixture
def client(plans_dir, auth_dir):
    from app.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def device_key(plans_dir, auth_dir):
    """Generate a device key for testing."""
    from app.auth_manager import generate_device_key
    return generate_device_key("test-device")


@pytest.fixture
def auth_headers(device_key):
    return {"Authorization": f"Bearer {device_key}"}


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_read_no_user_redirects(client):
    resp = await client.get("/.well-known/finger", follow_redirects=False)
    assert resp.status_code in (303, 307)


@pytest.mark.asyncio
async def test_read_no_status_returns_dash(client):
    resp = await client.get("/.well-known/finger?user=test")
    assert resp.status_code == 200
    assert resp.text == "-"


@pytest.mark.asyncio
async def test_write_without_auth_returns_401(client):
    resp = await client.put(
        "/.well-known/finger/test/plan",
        content="Should fail",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_write_and_read(client, auth_headers):
    resp = await client.put(
        "/.well-known/finger/test/plan",
        content="Hello from finger!",
        headers=auth_headers,
    )
    assert resp.status_code == 200

    resp = await client.get("/.well-known/finger?user=test")
    assert resp.status_code == 200
    assert resp.text == "Hello from finger!"


@pytest.mark.asyncio
async def test_delete(client, auth_headers):
    await client.put(
        "/.well-known/finger/test/plan",
        content="Temporary status",
        headers=auth_headers,
    )

    resp = await client.delete(
        "/.well-known/finger/test/plan",
        headers=auth_headers,
    )
    assert resp.status_code == 200

    resp = await client.get("/.well-known/finger?user=test")
    assert resp.text == "-"


@pytest.mark.asyncio
async def test_ttl_duration(client, auth_headers, plans_dir):
    await client.put(
        "/.well-known/finger/test/plan",
        content="Expiring soon",
        params={"ttl": "2s"},
        headers=auth_headers,
    )

    # Should be readable immediately
    resp = await client.get("/.well-known/finger?user=test")
    assert resp.text == "Expiring soon"

    # Wait for expiry
    time.sleep(3)

    resp = await client.get("/.well-known/finger?user=test")
    assert resp.text == "-"

    # Files should be cleaned up
    assert not (plans_dir / "test.md").exists()
    assert not (plans_dir / "test.meta").exists()


@pytest.mark.asyncio
async def test_ttl_iso_format(client, auth_headers):
    import datetime

    future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    resp = await client.put(
        "/.well-known/finger/test/plan",
        content="ISO TTL test",
        params={"ttl": future.isoformat()},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["expires_at"] is not None


@pytest.mark.asyncio
async def test_ttl_invalid_format(client, auth_headers):
    resp = await client.put(
        "/.well-known/finger/test/plan",
        content="Bad TTL",
        params={"ttl": "not a ttl"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_indefinite_ttl(client, auth_headers):
    resp = await client.put(
        "/.well-known/finger/test/plan",
        content="No expiry",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["expires_at"] is None


@pytest.mark.asyncio
async def test_sweep_expired(plans_dir, auth_dir):
    """Test the startup sweep function."""
    from app.storage import write_plan, sweep_expired, read_plan

    # Write a plan that expired 1 hour ago
    past = int(time.time()) - 3600
    write_plan("expired_user", "Gone", expires_at=past)

    # Write an indefinite plan
    write_plan("forever_user", "Staying")

    # Read should return None for expired (triggering cleanup)
    assert read_plan("expired_user") is None
    assert not (plans_dir / "expired_user.md").exists()

    # Sweep should find nothing (already cleaned by read)
    count = sweep_expired()
    assert count == 0

    # Indefinite plan should still be there
    assert read_plan("forever_user") == "Staying"


@pytest.mark.asyncio
async def test_auth_flow(client):
    """Test the full email magic link flow."""
    # Step 1: Request auth
    resp = await client.post("/.well-known/finger/request-auth")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Step 2: Find the token from the auth_tokens directory
    from app.auth_manager import generate_auth_token, consume_auth_token
    import os
    token_dir = Path(os.environ["FINGER_TOKEN_DIR"])
    tokens = list(token_dir.iterdir())
    assert len(tokens) > 0
    token = tokens[0].name

    # Step 3: Confirm auth
    resp = await client.post(
        "/.well-known/finger/confirm-auth",
        json={"token": token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["device_key"].startswith("sk-finger-")


@pytest.mark.asyncio
async def test_deauth(client, auth_headers, device_key):
    """Test deauth invalidates keys."""
    # Write a status
    resp = await client.put(
        "/.well-known/finger/test/plan",
        content="Will be deauthed",
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Deauth all keys
    resp = await client.post("/.well-known/finger/deauth")
    assert resp.status_code == 200
    assert resp.json()["revoked_keys"] >= 1

    # Old key should no longer work
    resp = await client.put(
        "/.well-known/finger/test/plan",
        content="Should fail",
        headers=auth_headers,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_keys(client, auth_headers):
    """Test listing keys (requires auth)."""
    resp = await client.get(
        "/.well-known/finger/keys",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "keys" in data
