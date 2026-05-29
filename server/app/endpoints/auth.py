"""Auth endpoints — email magic link key management."""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from ..auth_manager import (
    generate_auth_token,
    consume_auth_token,
    generate_device_key,
    revoke_all_keys,
    list_keys,
)
from ..mailer import send_auth_email
from ..dependencies import require_auth

logger = logging.getLogger("finger.auth")
router = APIRouter()


@router.post("/.well-known/finger/request-auth")
async def request_auth():
    """Request a magic link auth token. Sent via email to the configured address."""
    token, _ = generate_auth_token()

    sent = send_auth_email(token)
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send auth email")

    return {"status": "ok", "message": "Auth code sent to your email"}


@router.post("/.well-known/finger/confirm-auth")
async def confirm_auth(token: str = Body(..., embed=True)):
    """Exchange a magic link token for a long-lived device key."""
    if not consume_auth_token(token):
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    device_key = generate_device_key()
    return {"status": "ok", "device_key": device_key}


@router.post("/.well-known/finger/deauth")
async def deauth():
    """Invalidate all device keys for this account.
    Sends a confirmation code via email first (simple version: just do it).
    """
    count = revoke_all_keys()
    logger.info("Revoked %d device keys", count)
    return {"status": "ok", "revoked_keys": count}


@router.get("/.well-known/finger/keys", dependencies=[Depends(require_auth)])
async def list_active_keys():
    """List active device keys with metadata."""
    keys = list_keys()
    return {"status": "ok", "keys": keys}
