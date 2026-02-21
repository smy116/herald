"""Telegram Bot channel handler."""

import httpx

from app.channels import ChannelHandler, register


@register
class TelegramHandler(ChannelHandler):
    type_name = "telegram"
    display_name = "Telegram"
    icon = "ri-telegram-line"
    config_schema = [
        {"key": "bot_token", "label": "Bot Token", "type": "password", "required": True, "placeholder": "123456:ABC-..."},
        {"key": "chat_id", "label": "Chat ID", "type": "text", "required": True, "placeholder": "-100..."},
    ]

    async def send(self, config: dict, title: str, body: str) -> None:
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
            if resp.status_code != 200:
                error_desc = resp.text
                try:
                    error_data = resp.json()
                    error_desc = error_data.get("description", resp.text)
                except Exception:
                    pass
                raise ValueError(f"Telegram API Error ({resp.status_code}): {error_desc}")
            resp.raise_for_status()
