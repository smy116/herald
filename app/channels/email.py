"""Email (SMTP) channel handler — async wrapper around smtplib."""

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.channels import ChannelHandler, register
from app.config import settings


@register
class EmailHandler(ChannelHandler):
    type_name = "email"
    display_name = "Email"
    icon = "ri-mail-line"
    config_schema = [
        {"key": "to", "label": "收件邮箱", "type": "email", "required": True, "placeholder": "user@example.com"},
    ]

    async def send(self, config: dict, title: str, body: str) -> None:
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

        # Run blocking SMTP in a thread to avoid blocking the event loop
        await asyncio.to_thread(self._smtp_send, host, port, user, password, from_addr, to_addr, msg)

    @staticmethod
    def _smtp_send(host, port, user, password, from_addr, to_addr, msg):
        with smtplib.SMTP_SSL(host, port, timeout=15) as server:
            server.login(user, password)
            server.sendmail(from_addr, [to_addr], msg.as_string())
