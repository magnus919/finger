"""
FastAPI dependencies for device key auth.
"""

from fastapi import Header, HTTPException

from .auth_manager import verify_device_key


async def require_auth(authorization: str | None = Header(default=None)):
    """Dependency: reject requests without a valid device key."""
    if not verify_device_key(authorization):
        raise HTTPException(status_code=401, detail="Invalid or missing device key")
