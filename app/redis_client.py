import os

from dotenv import load_dotenv
from redis import asyncio as aioredis


load_dotenv()


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6376"
)

QUEUE_NAME = "ai_tasks_queue"
STATUS_PREFIX = "task_status:"


redis_client = aioredis.from_url(
    REDIS_URL,
    decode_responses=True
)