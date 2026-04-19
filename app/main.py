import os
from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.batch import router as batch_router
from app.api.chapters import router as chapters_router
from app.api.cover import router as cover_router
from app.api.jobs import router as jobs_router, jobs_router as jobs_base_router
from app.api.templates import router as templates_router
from app.config import settings
from app.core.logging import setup_logging
from supabase import create_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
    # Startup
    app.state.supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
    amqp_connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    app.state.amqp_connection = amqp_connection
    app.state.amqp_channel = await amqp_connection.channel()
    yield
    # Shutdown
    await app.state.amqp_connection.close()


app = FastAPI(title="Book Generation Engine", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)
app.include_router(jobs_base_router)
app.include_router(chapters_router)
app.include_router(admin_router)
app.include_router(batch_router)
app.include_router(cover_router)
app.include_router(templates_router)
