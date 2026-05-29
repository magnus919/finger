"""
Device key management for finger.

Keys are stored in /data/keys.json. Each entry is:
  {
    "key_hash": "<sha256 of the key>",
    "key_prefix": "<first 8 chars of raw key>",
    "created_at": <unix ts>,
    "last_used": <unix ts>,
    "label": "<user-provided device name or null>"
  }
"""

import hashlib
import json
import os
import secrets
import time
from pathlib import Path

KEYS_PATH = Path(os.environ.get("FINGER_KEYS_PATH", "/data/keys.json"))


def _load_keys() -> list[dict]:
    if not KEYS_PATH.exists():
        return []
    try:
        return json.loads(KEYS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def _save_keys(keys: list[dict]) -> None:
    KEYS_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEYS_PATH.write_text(json.dumps(keys, indent=2))


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def generate_device_key(label: str | None = None) -> str:
    """Generate a new device key, store it, return the raw key."""
    raw = "sk-finger-" + secrets.token_hex(32)
    entry = {
        "key_hash": _hash_key(raw),
        "key_prefix": raw[:18] + "...",
        "created_at": int(time.time()),
        "last_used": int(time.time()),
        "label": label or None,
    }
    keys = _load_keys()
    keys.append(entry)
    _save_keys(keys)
    return raw


def verify_device_key(auth_header: str | None) -> bool:
    """Check if an Authorization header contains a valid device key."""
    if not auth_header:
        return False
    if not auth_header.startswith("Bearer "):
        return False
    key = auth_header[len("Bearer "):]
    key_hash = _hash_key(key)
    keys = _load_keys()
    for entry in keys:
        if entry["key_hash"] == key_hash:
            # Update last_used
            entry["last_used"] = int(time.time())
            _save_keys(keys)
            return True
    return False


def revoke_all_keys() -> int:
    """Remove all device keys. Returns count of keys removed."""
    count = len(_load_keys())
    _save_keys([])
    return count


def list_keys() -> list[dict]:
    """Return key metadata (without hashes) for display."""
    return [
        {
            "prefix": k["key_prefix"],
            "created_at": k["created_at"],
            "last_used": k["last_used"],
            "label": k.get("label"),
        }
        for k in _load_keys()
    ]


def generate_auth_token() -> tuple[str, str]:
    """Generate a short-lived auth token. Returns (token, filename)."""
    token = secrets.token_hex(16)
    expiry = int(time.time()) + 900  # 15 minutes
    token_dir = Path(os.environ.get("FINGER_TOKEN_DIR", "/data/auth_tokens"))
    token_dir.mkdir(parents=True, exist_ok=True)
    token_file = token_dir / token
    token_file.write_text(json.dumps({"expires_at": expiry}))
    return token, str(token_file)


def consume_auth_token(token: str) -> bool:
    """Validate and consume an auth token. Returns True if valid."""
    token_dir = Path(os.environ.get("FINGER_TOKEN_DIR", "/data/auth_tokens"))
    token_file = token_dir / token
    if not token_file.exists():
        return False
    try:
        data = json.loads(token_file.read_text())
        if time.time() > data.get("expires_at", 0):
            token_file.unlink(missing_ok=True)
            return False
        token_file.unlink(missing_ok=True)
        return True
    except (json.JSONDecodeError, OSError):
        return False
