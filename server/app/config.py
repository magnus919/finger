"""
Configuration for the finger server.

All config comes from environment variables (or .env file).
"""

import os


def get_config() -> dict:
    return {
        "user": os.environ.get("FINGER_USER", ""),
        "host": os.environ.get("FINGER_HOST", ""),
        "plans_dir": os.environ.get("FINGER_PLANS_DIR", "/data/plans"),
    }
