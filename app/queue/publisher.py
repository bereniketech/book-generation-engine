"""Publish book generation jobs to RabbitMQ."""
from __future__ import annotations

import json

import aio_pika

from app.queue.connection import QUEUE_NAME


async def publish_job(channel: aio_pika.Channel, job_id: str, config: dict) -> None:
    """Publish a job message to the book_jobs queue."""
    payload = json.dumps({"job_id": job_id, "config": config})
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=payload.encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=QUEUE_NAME,
    )
