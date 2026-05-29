"""
Parse TTL expressions into unix timestamps.

Acceptable input formats:
  - Duration: "30m", "2h30m", "1d", "45s"
  - Absolute ISO datetime: "2026-06-01T12:00:00Z", "2026-06-01 12:00:00"
"""

import re
import time
from datetime import datetime, timezone


def parse_ttl(ttl: str) -> int | None:
    """Parse a TTL string into a unix timestamp (int), or return None for no expiry."""
    if not ttl or not ttl.strip():
        return None

    ttl = ttl.strip()

    # Try duration format: e.g. "2h30m", "1d", "45s"
    dur_match = re.fullmatch(
        r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", ttl
    )
    if dur_match and any(g is not None for g in dur_match.groups()):
        days = int(dur_match.group(1) or 0)
        hours = int(dur_match.group(2) or 0)
        minutes = int(dur_match.group(3) or 0)
        seconds = int(dur_match.group(4) or 0)
        total = days * 86400 + hours * 3600 + minutes * 60 + seconds
        if total == 0:
            return None
        return int(time.time()) + total

    # Try ISO datetime format
    try:
        dt = datetime.fromisoformat(ttl.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except (ValueError, TypeError):
        raise ValueError(f"Invalid TTL format: {ttl}")
