"""Read endpoint — GET /.well-known/finger"""

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from .. import storage

router = APIRouter()


@router.get("/.well-known/finger")
async def finger_read(
    request: Request,
    user: str = Query(default=None),
):
    """Return a user's finger status, or redirect if no user specified."""
    if not user:
        root = f"{request.url.scheme}://{request.url.netloc}"
        return RedirectResponse(url=root)

    content = storage.read_plan(user)

    if content is None:
        return PlainTextResponse("-")

    return PlainTextResponse(content)
