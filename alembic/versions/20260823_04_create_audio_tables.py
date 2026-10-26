"""创建音频主表和转写片段表。"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260823_04"
down_revision: str | Sequence[str] | None = "20260823_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audio_documents",
        sa.Column("audio_id", sa.String(80), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255)),
        sa.Column("stored_path", sa.String(1024)),
        sa.Column("duration_ms", mysql.BIGINT(unsigned=True), nullable=False, server_default="0"),
        sa.Column("language", sa.String(32)),
        sa.Column("visibility", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="processing"),
        sa.Column("source_mode", sa.String(32), nullable=False, server_default="asr"),
        sa.Column("error_message", sa.String(500)),
        sa.Column("uploader_user_id", mysql.BIGINT(unsigned=True)),
        sa.Column("uploader_username", sa.String(64)),
        sa.Column("segment_count", mysql.INTEGER(unsigned=True), nullable=False, server_default="0"),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(["uploader_user_id"], ["users.id"], ondelete="SET NULL"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_table(
        "audio_segments",
        sa.Column("audio_id", sa.String(80), nullable=False),
        sa.Column("segment_idx", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("start_ms", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("end_ms", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("text", mysql.MEDIUMTEXT(), nullable=False),
        sa.ForeignKeyConstraint(["audio_id"], ["audio_documents.audio_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("audio_id", "segment_idx"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_audio_documents_visibility", "audio_documents", ["visibility"])
    op.create_index("ix_audio_documents_status", "audio_documents", ["status"])


def downgrade() -> None:
    op.drop_table("audio_segments")
    op.drop_index("ix_audio_documents_status", table_name="audio_documents")
    op.drop_index("ix_audio_documents_visibility", table_name="audio_documents")
    op.drop_table("audio_documents")