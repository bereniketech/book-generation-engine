"""RabbitMQ connection helper."""
from __future__ import annotations

import aio_pika

QUEUE_NAME = "bookgen.jobs"
DLQ_NAME = "bookgen.dlq"
DLQ_EXCHANGE_NAME = "bookgen.dlq"


async def get_connection(url: str) -> aio_pika.Connection:
    return await aio_pika.connect_robust(url)


async def declare_queue(channel: aio_pika.Channel) -> aio_pika.Queue:
    # Declare DLQ exchange first
    dlq_exchange = await channel.declare_exchange(
        DLQ_EXCHANGE_NAME,
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    # Declare DLQ queue bound to DLQ exchange
    dlq_queue = await channel.declare_queue(
        DLQ_NAME,
        durable=True,
        arguments={},
    )
    await dlq_queue.bind(dlq_exchange, routing_key=DLQ_NAME)

    # Declare main jobs queue with DLQ redirect
    jobs_queue = await channel.declare_queue(
        QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": DLQ_EXCHANGE_NAME,
            "x-dead-letter-routing-key": DLQ_NAME,
            "x-message-ttl": 86_400_000,  # 24 hours
        },
    )
    return jobs_queue
