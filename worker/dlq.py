"""Dead-letter queue consumer — logs dead messages and supports retry."""
from __future__ import annotations

import json
import os
from typing import Any

import aio_pika

from app.core.logging import get_logger

log = get_logger(__name__)

RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

# In-memory DLQ store (for API inspection without RabbitMQ Management API dependency)
_dlq_messages: list[dict[str, Any]] = []


async def start_dlq_consumer() -> None:
    """Start consuming DLQ messages and log them. Run as background task."""
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    dlq_queue = await channel.declare_queue("bookgen.dlq", durable=True)

    async with dlq_queue.iterator() as messages:
        async for message in messages:
            async with message.process(requeue=False):
                try:
                    body = json.loads(message.body)
                    retry_count = int(message.headers.get("x-death-count", 0))
                    job_id = body.get("job_id", "unknown")
                    error = body.get("error", "unknown")

                    log.error(
                        "worker.dlq.routed",
                        job_id=job_id,
                        retry_count=retry_count,
                        error=error,
                        queue="bookgen.dlq",
                    )

                    _dlq_messages.append({
                        "job_id": job_id,
                        "retry_count": retry_count,
                        "error": error,
                        "queued_at": str(message.timestamp) if message.timestamp else "unknown",
                        "body": body,
                    })

                    # Keep only last 100 messages in memory
                    if len(_dlq_messages) > 100:
                        _dlq_messages.pop(0)

                except Exception as exc:
                    log.error("worker.dlq.process_error", error=str(exc))


async def retry_dlq_messages() -> int:
    """Re-publish all in-memory DLQ messages to the main jobs queue. Returns count requeued."""
    if not _dlq_messages:
        return 0

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    exchange = await channel.get_exchange("", ensure=False)  # default exchange

    requeued = 0
    for msg in list(_dlq_messages):
        body = msg.get("body", {})
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="bookgen.jobs",
        )
        requeued += 1

    _dlq_messages.clear()
    log.info("worker.dlq.retried", requeued=requeued)
    await connection.close()
    return requeued


def get_dlq_status() -> dict:
    """Return current DLQ message count and sample (up to 10)."""
    return {
        "count": len(_dlq_messages),
        "sample": _dlq_messages[:10],
    }
