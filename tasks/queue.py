from __future__ import annotations

from flask import current_app
from redis import Redis
from rq import Queue


def get_redis_connection() -> Redis:
    return Redis.from_url(current_app.config["REDIS_URL"])


def get_queue(name: str | None = None) -> Queue:
    queue_name = name or current_app.config["RQ_DEFAULT_QUEUE"]
    return Queue(queue_name, connection=get_redis_connection())
