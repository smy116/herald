"""Simple cookie-based authentication for the admin dashboard."""

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer

from app.config import settings

COOKIE_NAME = "herald_session"
MAX_AGE = 86400 * 7  # 7 days

_serializer = URLSafeTimedSerializer(settings.HERALD_SECRET)


def create_session_cookie(response, value: str = "authenticated"):
    """Set a signed session cookie on the response."""
    token = _serializer.dumps(value)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


def clear_session_cookie(response):
    """Remove the session cookie."""
    response.delete_cookie(COOKIE_NAME)
    return response


def verify_session(request: Request) -> bool:
    """Check if the request has a valid session cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    try:
        _serializer.loads(token, max_age=MAX_AGE)
        return True
    except Exception:
        return False


async def require_login(request: Request):
    """FastAPI dependency — redirects to /login if not authenticated."""
    if not verify_session(request):
        raise HTTPException(status_code=303, headers={"Location": "/login"})
