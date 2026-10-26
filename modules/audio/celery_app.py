from celery import Celery

from core.config import settings


celery_app = Celery(
    "kb_assistant",
    broker=settings.celery_broker_url,
    include=["modules.audio.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_routes={"modules.audio.tasks.*": {"queue": "audio"}},
    task_track_started=True,
    task_ignore_result=True,  # 任务状态统一从 MySQL 查询。
    worker_prefetch_multiplier=1,
    task_publish_retry=False,
    broker_connection_timeout=3,
    broker_transport_options={"socket_connect_timeout": 3, "socket_timeout": 3},
    timezone="Asia/Shanghai",
)