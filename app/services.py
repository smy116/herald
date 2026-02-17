"""Message dispatch services for Webhook, Telegram, and Email channels."""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx
from sqlalchemy.orm import Session

from app.models import Channel, MessageLog
from app.config import settings


async def dispatch_message(
    db: Session,
    title: str,
    body: str,
    channels: list[Channel],
    api_key_name: str = "",
) -> list[MessageLog]:
    """Send a message to each channel and record the results."""
    logs = []
    for ch in channels:
        log = MessageLog(
            title=title,
            body=body,
            channel_name=ch.name,
            api_key_name=api_key_name,
            status="pending",
        )
        try:
            config = json.loads(ch.config) if isinstance(ch.config, str) else ch.config
            if ch.type == "webhook":
                await _send_webhook(config, title, body)
            elif ch.type == "telegram":
                await _send_telegram(config, title, body)
            elif ch.type == "email":
                _send_email(config, title, body)
            log.status = "success"
        except Exception as e:
            log.status = "failed"
            log.error_msg = str(e)[:1000]
        db.add(log)
        logs.append(log)
    db.commit()
    return logs


# ── Webhook ──────────────────────────────────────────────

async def _send_webhook(config: dict, title: str, body: str):
    url = config.get("url", "")
    if not url:
        raise ValueError("Webhook URL is empty")
    method = config.get("method", "POST").upper()
    content_type = config.get("content_type", "json")  # json | form
    body_template = config.get("body_template", "")
    custom_headers = config.get("headers", {})  # user-defined headers

    # Build payload from template or use default
    if body_template.strip():
        rendered = body_template.replace("{{title}}", title).replace("{{body}}", body)
        if content_type == "form":
            try:
                payload = json.loads(rendered)
            except json.JSONDecodeError:
                payload = {"body": rendered}
        else:
            payload = json.loads(rendered)
    else:
        payload = {"title": title, "body": body}

    async with httpx.AsyncClient(timeout=15) as client:
        if content_type == "form":
            resp = await client.request(method, url, data=payload, headers=custom_headers or None)
        else:
            resp = await client.request(method, url, json=payload, headers=custom_headers or None)
        resp.raise_for_status()


# ── Telegram ─────────────────────────────────────────────

async def _send_telegram(config: dict, title: str, body: str):
    bot_token = config.get("bot_token", "")
    chat_id = config.get("chat_id", "")
    if not bot_token or not chat_id:
        raise ValueError("Telegram bot_token or chat_id is empty")

    text = f"*{title}*\n{body}" if body else f"*{title}*"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        )
        resp.raise_for_status()


# ── Email (SMTP) ─────────────────────────────────────────

def _send_email(config: dict, title: str, body: str):
    to_addr = config.get("to", "")
    if not to_addr:
        raise ValueError("Email recipient (to) is empty")

    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    user = settings.SMTP_USER
    password = settings.SMTP_PASSWORD
    from_addr = settings.SMTP_FROM or user

    if not host or not user:
        raise ValueError("SMTP not configured (set SMTP_HOST / SMTP_USER env vars)")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = title
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(body or title, "plain", "utf-8"))

    with smtplib.SMTP_SSL(host, port, timeout=15) as server:
        server.login(user, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())
