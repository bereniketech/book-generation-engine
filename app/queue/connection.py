"""RabbitMQ connection helper."""
from __future__ import annotations

import aio_pika

QUEUE_NAME = "book_jobs"


async def get_connection(url: str) -> aio_pika.Connection:
    return await aio_pika.connect_robust(url)


async def declare_queue(channel: aio_pika.Channel) -> aio_pika.Queue:
    return await channel.declare_queue(QUEUE_NAME, durable=True)
