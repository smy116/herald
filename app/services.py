"""Message dispatch service — uses the channel handler registry."""

import asyncio
import json
import logging

from sqlalchemy.orm import Session

from app.models import Channel, MessageLog
from app.channels import get_handler

logger = logging.getLogger(__name__)

# Retry settings
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1  # seconds, exponential backoff: 1s, 2s, 4s


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
            retry_count=0,
        )
        config = json.loads(ch.config) if isinstance(ch.config, str) else ch.config
        handler = get_handler(ch.type)

        # Attempt with automatic retries (exponential backoff)
        for attempt in range(MAX_RETRIES + 1):
            try:
                await handler.send(config, title, body)
                log.status = "success"
                break
            except Exception as e:
                log.status = "failed"
                log.error_msg = str(e)[:1000]
                if attempt < MAX_RETRIES:
                    log.retry_count = attempt + 1
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Channel %s attempt %d failed: %s — retrying in %ds",
                        ch.name, attempt + 1, e, delay,
                    )
                    await asyncio.sleep(delay)

        db.add(log)
        logs.append(log)
    db.commit()
    return logs
