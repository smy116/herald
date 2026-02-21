"""FastAPI application entry point — page routes, /send webhook, and auth."""

import datetime
import json

from fastapi import FastAPI, Request, Depends, Form, Query, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import get_db, init_db
from app.models import Channel, APIKey, MessageLog
from app.schemas import ApiResponse
from app.auth import require_login, verify_session, create_session_cookie, clear_session_cookie
from app.services import dispatch_message
from app.api import router as api_router

# Setup slowapi rate limiter based on client IP
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Herald", docs_url=None, redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include RPC API router
app.include_router(api_router)


@app.on_event("startup")
async def startup():
    init_db()


# ── Jinja2 Helpers ───────────────────────────────────────

def _ctx(request: Request, **kwargs):
    """Build template context with common variables."""
    kwargs["request"] = request
    return kwargs


# ── Auth Routes ──────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if verify_session(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", _ctx(request))


@app.post("/login")
async def login_submit(request: Request, password: str = Form(...)):
    if password != settings.HERALD_SECRET:
        return templates.TemplateResponse(
            "login.html", _ctx(request, error="密码错误"), status_code=401
        )
    resp = RedirectResponse("/", status_code=302)
    create_session_cookie(resp)
    return resp


@app.get("/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=302)
    clear_session_cookie(resp)
    return resp


# ── Page Routes (SSR, require login) ────────────────────

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def page_index(request: Request, db: Session = Depends(get_db)):
    total_channels = db.query(Channel).count()
    total_keys = db.query(APIKey).count()

    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_msgs = db.query(MessageLog).filter(MessageLog.created_at >= today_start).count()
    today_failed = (
        db.query(MessageLog)
        .filter(MessageLog.created_at >= today_start, MessageLog.status == "failed")
        .count()
    )

    recent_logs = (
        db.query(MessageLog).order_by(MessageLog.created_at.desc()).limit(10).all()
    )

    stats = {
        "total_channels": total_channels,
        "total_keys": total_keys,
        "today_msgs": today_msgs,
        "today_failed": today_failed,
    }
    return templates.TemplateResponse(
        "index.html", _ctx(request, stats=stats, recent_logs=recent_logs)
    )


@app.get("/channels", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def page_channels(request: Request, db: Session = Depends(get_db)):
    channels = db.query(Channel).order_by(Channel.created_at.desc()).all()
    # Parse config JSON for template display
    for ch in channels:
        try:
            ch._config_dict = json.loads(ch.config) if ch.config else {}
        except Exception:
            ch._config_dict = {}
    return templates.TemplateResponse("channels.html", _ctx(request, channels=channels))


@app.get("/keys", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def page_keys(request: Request, db: Session = Depends(get_db)):
    keys = db.query(APIKey).order_by(APIKey.created_at.desc()).all()
    return templates.TemplateResponse("keys.html", _ctx(request, keys=keys))


@app.get("/logs", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def page_logs(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    page_size = 20
    total = db.query(MessageLog).count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    logs = (
        db.query(MessageLog)
        .order_by(MessageLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return templates.TemplateResponse(
        "logs.html",
        _ctx(request, logs=logs, page=page, total_pages=total_pages),
    )


# ── Public Webhook Endpoint ──────────────────────────────

@app.post("/send")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def webhook_send(
    request: Request,
    db: Session = Depends(get_db),
    key: Optional[str] = Query(None),
    x_api_key: Optional[str] = Header(None),
):
    # --- Auth ---
    api_key_value = None
    if x_api_key:
        api_key_value = x_api_key.strip()
    elif key:
        api_key_value = key.strip()

    if not api_key_value:
        return JSONResponse(
            status_code=401,
            content=ApiResponse(ok=False, msg="Missing API key").model_dump(),
        )

    api_key = (
        db.query(APIKey)
        .filter(APIKey.key == api_key_value)
        .first()
    )
    if not api_key:
        return JSONResponse(
            status_code=401,
            content=ApiResponse(ok=False, msg="Invalid or revoked API key").model_dump(),
        )

    # --- Parse body (JSON or Form) ---
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    title = data.get("title", "").strip()
    body = data.get("body", "").strip()
    channels_str = (data.get("channels") or data.get("channel") or "").strip()

    if not title:
        return JSONResponse(
            status_code=400,
            content=ApiResponse(ok=False, msg="title is required").model_dump(),
        )

    # --- Resolve channels ---
    if channels_str:
        names = [n.strip() for n in channels_str.split(",") if n.strip()]
        channels = (
            db.query(Channel)
            .filter(Channel.name.in_(names), Channel.enabled == True)
            .all()
        )
        if not channels:
            return JSONResponse(
                status_code=404,
                content=ApiResponse(ok=False, msg=f"Channel(s) not found or disabled: {channels_str}").model_dump(),
            )
    else:
        channels = (
            db.query(Channel)
            .filter(Channel.is_default == True, Channel.enabled == True)
            .all()
        )
        if not channels:
            return JSONResponse(
                status_code=404,
                content=ApiResponse(ok=False, msg="No default channels configured").model_dump(),
            )

    # --- Dispatch ---
    logs = await dispatch_message(db, title, body, channels, api_key_name=api_key.name)

    failed = [l for l in logs if l.status == "failed"]
    if failed:
        return JSONResponse(
            status_code=207,
            content=ApiResponse(
                ok=False,
                msg=f"{len(failed)}/{len(logs)} channel(s) failed",
                data=[{"channel": l.channel_name, "error": l.error_msg} for l in failed],
            ).model_dump(),
        )

    return ApiResponse(msg=f"Sent to {len(logs)} channel(s)")
