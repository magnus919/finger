"""
Storage layer for finger plan files.

Layout:
  /data/plans/<user>.md      — status content (markdown text)
  /data/plans/<user>.meta    — {"expires_at": <unix_ts|null>}

expires_at of null means indefinite (default).
If expires_at is in the past, the plan is treated as nonexistent.
"""

import json
import os
import time
from pathlib import Path

PLANS_DIR = Path(os.environ.get("FINGER_PLANS_DIR", "/data/plans"))


def _plan_path(user: str) -> Path:
    return PLANS_DIR / f"{user}.md"


def _meta_path(user: str) -> Path:
    return PLANS_DIR / f"{user}.meta"


def read_plan(user: str) -> str | None:
    """Return the plan content, or None if no plan exists or it has expired."""
    meta = _meta_path(user)
    plan = _plan_path(user)

    # Check expiry
    if meta.exists():
        try:
            data = json.loads(meta.read_text())
            expires_at = data.get("expires_at")
            if expires_at is not None and time.time() > expires_at:
                # Expired — clean up
                meta.unlink(missing_ok=True)
                plan.unlink(missing_ok=True)
                return None
        except (json.JSONDecodeError, OSError):
            pass

    if not plan.exists():
        return None

    return plan.read_text(encoding="utf-8")


def write_plan(user: str, content: str, expires_at: int | None = None) -> None:
    """Write a plan file and optional TTL metadata."""
    PLANS_DIR.mkdir(parents=True, exist_ok=True)

    _plan_path(user).write_text(content, encoding="utf-8")

    meta = {"expires_at": expires_at}
    _meta_path(user).write_text(json.dumps(meta), encoding="utf-8")


def delete_plan(user: str) -> None:
    """Remove both plan and metadata files."""
    _plan_path(user).unlink(missing_ok=True)
    _meta_path(user).unlink(missing_ok=True)


def sweep_expired() -> int:
    """Remove all expired plan files. Returns count of expired plans removed."""
    if not PLANS_DIR.exists():
        return 0

    now = time.time()
    count = 0
    for meta_file in PLANS_DIR.glob("*.meta"):
        try:
            data = json.loads(meta_file.read_text())
            expires_at = data.get("expires_at")
            if expires_at is not None and now > expires_at:
                user = meta_file.stem
                _plan_path(user).unlink(missing_ok=True)
                meta_file.unlink(missing_ok=True)
                count += 1
        except (json.JSONDecodeError, OSError):
            continue

    return count
