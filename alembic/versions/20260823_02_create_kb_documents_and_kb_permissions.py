"""创建知识文档表，并增加 admin 和知识库管理权限。"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260823_02"
down_revision: str | Sequence[str] | None = "20260823_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = [
    "kb.manage_docs", "kb.view_internal", "kb.view_public",
    "system.manage_roles", "system.manage_users",
]


def upgrade() -> None:
    op.create_table(
        "kb_documents",
        sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("stored_name", sa.String(255), nullable=False),
        sa.Column("source_path", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("visibility", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_by", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.UniqueConstraint("source_path", name="uq_kb_documents_source_path"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    roles = sa.table("roles", sa.column("code", sa.String), sa.column("name", sa.String))
    permissions = sa.table("permissions", sa.column("code", sa.String))
    role_permissions = sa.table(
        "role_permissions", sa.column("role_code", sa.String), sa.column("permission_code", sa.String)
    )
    op.bulk_insert(roles, [{"code": "admin", "name": "系统管理员"}])
    op.bulk_insert(permissions, [{"code": code} for code in PERMISSIONS])
    op.bulk_insert(
        role_permissions,
        [{"role_code": "public", "permission_code": "kb.view_public"}]
        + [{"role_code": "admin", "permission_code": code} for code in PERMISSIONS],
    )


def downgrade() -> None:
    op.execute("UPDATE users SET role_code='public' WHERE role_code='admin'")
    codes = ", ".join(f"'{code}'" for code in PERMISSIONS)
    op.execute(f"DELETE FROM role_permissions WHERE permission_code IN ({codes})")
    op.execute(f"DELETE FROM permissions WHERE code IN ({codes})")
    op.execute("DELETE FROM roles WHERE code='admin'")
    op.drop_table("kb_documents")