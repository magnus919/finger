"""Write endpoints — PUT/DELETE /.well-known/finger/<user>/plan"""

from fastapi import APIRouter, Body, Depends, Query, HTTPException

from .. import storage
from ..ttl import parse_ttl
from ..dependencies import require_auth

router = APIRouter()


@router.put("/.well-known/finger/{user}/plan", dependencies=[Depends(require_auth)])
async def finger_write(
    user: str,
    body: str = Body(..., media_type="text/plain"),
    ttl: str = Query(default=None),
):
    """Set a finger status. Body is the markdown text. Requires auth."""
    try:
        expires_at = parse_ttl(ttl) if ttl else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    storage.write_plan(user, body, expires_at)
    return {"status": "ok", "user": user, "expires_at": expires_at}


@router.delete("/.well-known/finger/{user}/plan", dependencies=[Depends(require_auth)])
async def finger_delete(user: str):
    """Clear a finger status. Requires auth."""
    storage.delete_plan(user)
    return {"status": "ok", "user": user}
