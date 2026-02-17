"""Webhook channel handler with Jinja2 sandboxed template rendering."""

import json
import httpx
from jinja2.sandbox import SandboxedEnvironment

from app.channels import ChannelHandler, register

_sandbox = SandboxedEnvironment()


@register
class WebhookHandler(ChannelHandler):
    type_name = "webhook"
    display_name = "Webhook"
    icon = "ri-webhook-line"
    config_schema = [
        {"key": "url", "label": "URL", "type": "url", "required": True, "placeholder": "https://..."},
        {
            "key": "method",
            "label": "Method",
            "type": "select",
            "required": False,
            "options": ["GET", "POST"],
            "default": "POST",
        },
        {
            "key": "content_type",
            "label": "Content-Type",
            "type": "select",
            "required": False,
            "options": ["json", "form"],
            "default": "json",
        },
        {
            "key": "headers_text",
            "label": "自定义 Headers",
            "type": "textarea",
            "required": False,
            "placeholder": "每行一个，格式: Key: Value",
            "rows": 2,
        },
        {
            "key": "body_template",
            "label": "自定义 Body",
            "type": "textarea",
            "required": False,
            "placeholder": '留空则默认: {"title":"...","body":"..."}',
            "hint": "可用变量: {{title}} {{body}}",
            "rows": 3,
        },
    ]

    async def send(self, config: dict, title: str, body: str) -> None:
        url = config.get("url", "")
        if not url:
            raise ValueError("Webhook URL is empty")

        method = config.get("method", "POST").upper()
        content_type = config.get("content_type", "json")
        body_template = config.get("body_template", "")
        custom_headers = config.get("headers", {})

        # Build payload — use Jinja2 sandbox for template rendering
        if body_template.strip():
            rendered = _sandbox.from_string(body_template).render(title=title, body=body)
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
