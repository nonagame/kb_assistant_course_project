"""创建音频异步任务表。"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260823_05"
down_revision: str | Sequence[str] | None = "20260823_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audio_jobs",
        sa.Column("job_id", sa.String(80), primary_key=True),
        sa.Column("audio_id", sa.String(80), nullable=False),
        sa.Column("celery_task_id", sa.String(80)),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("progress", mysql.INTEGER(unsigned=True), nullable=False, server_default="0"),
        sa.Column("message", sa.String(500)),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(["audio_id"], ["audio_documents.audio_id"], ondelete="CASCADE"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_audio_jobs_audio_id", "audio_jobs", ["audio_id"])


def downgrade() -> None:
    op.drop_index("ix_audio_jobs_audio_id", table_name="audio_jobs")
    op.drop_table("audio_jobs")