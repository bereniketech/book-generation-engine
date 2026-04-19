"""RabbitMQ worker entrypoint."""
from __future__ import annotations

import asyncio
import json
import os

import aio_pika

from app.core.logging import get_logger, setup_logging
from app.queue.connection import QUEUE_NAME, declare_queue, get_connection
from app.services.progress import publish_progress
from supabase import create_client
from worker.pipeline.base import JobConfig
from worker.pipeline.runner import PipelineRunner

setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost/")


def _make_progress_callback(loop: asyncio.AbstractEventLoop):
    """Return a sync progress callback that publishes events to Redis via the given event loop."""

    def _on_progress(event: dict) -> None:
        job_id = event.get("job_id", "")
        logger.info("Progress: %s", event)
        # Schedule the async publish on the running event loop (thread-safe)
        asyncio.run_coroutine_threadsafe(publish_progress(job_id, event), loop)

    return _on_progress


async def process_message(message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        body = json.loads(message.body.decode())
        job_id = body["job_id"]
        config_dict = body["config"]
        logger.info("Processing job %s", job_id)
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        config = JobConfig(job_id=job_id, **config_dict)
        loop = asyncio.get_running_loop()
        progress_callback = _make_progress_callback(loop)
        runner = PipelineRunner(config=config, supabase=supabase, progress_callback=progress_callback)
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
