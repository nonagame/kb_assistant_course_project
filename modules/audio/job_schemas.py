from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AudioJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    job_id: str
    audio_id: str
    celery_task_id: str | None
    status: str
    progress: int
    message: str | None
    created_at: datetime
    updated_at: datetime