"""RabbitMQ worker entrypoint."""
from __future__ import annotations

import asyncio
import json
import logging
import os

import aio_pika

from app.queue.connection import QUEUE_NAME, declare_queue, get_connection
from supabase import create_client
from worker.pipeline.base import JobConfig
from worker.pipeline.runner import PipelineRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost/")

# In-memory progress event store for WebSocket broadcast (replaced by Redis pub/sub in production)
_progress_events: dict[str, list[dict]] = {}


def _on_progress(event: dict) -> None:
    job_id = event.get("job_id", "")
    if job_id not in _progress_events:
        _progress_events[job_id] = []
    _progress_events[job_id].append(event)
    logger.info("Progress: %s", event)


async def process_message(message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        body = json.loads(message.body.decode())
        job_id = body["job_id"]
        config_dict = body["config"]
        logger.info("Processing job %s", job_id)
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        config = JobConfig(job_id=job_id, **config_dict)
        runner = PipelineRunner(config=config, supabase=supabase, progress_callback=_on_progress)
        try:
            runner.run()
        except Exception as exc:
            logger.exception("Job %s failed: %s", job_id, exc)
            supabase.table("jobs").update({"status": "failed"}).eq("id", job_id).execute()


async def main() -> None:
    connection = await get_connection(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await declare_queue(channel)
        logger.info("Worker ready. Waiting for jobs on queue '%s'...", QUEUE_NAME)
        await queue.consume(process_message)
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
