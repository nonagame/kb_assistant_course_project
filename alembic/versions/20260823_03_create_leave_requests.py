"""创建请假表，并增加 HR 角色与请假权限。"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260823_03"
down_revision: str | Sequence[str] | None = "20260823_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LEAVE_PERMISSIONS = [
    "leave.apply",
    "leave.approve",
    "leave.cancel",
    "leave.modify",
    "leave.reject",
    "leave.view_all",
    "leave.view_self",
]


def upgrade() -> None:
    op.create_table(
        "leave_requests",
        sa.Column(
            "id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
        ),
        sa.Column("leave_id", sa.String(32), nullable=False),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("requester", sa.String(50), nullable=False),
        sa.Column("leave_type", sa.String(32), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("duration_days", sa.Numeric(8, 2), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("approver_user_id", mysql.BIGINT(unsigned=True)),
        sa.Column("decision_reason", sa.Text()),
        sa.Column("decided_at", mysql.DATETIME(fsp=6)),
        sa.Column(
            "created_at", mysql.DATETIME(fsp=6), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
        ),
        sa.Column(
            "updated_at", mysql.DATETIME(fsp=6), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approver_user_id"], ["users.id"]),
        sa.UniqueConstraint("leave_id", name="uq_leave_requests_leave_id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    roles = sa.table(
        "roles", sa.column("code", sa.String), sa.column("name", sa.String)
    )
    permissions = sa.table("permissions", sa.column("code", sa.String))
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_code", sa.String),
        sa.column("permission_code", sa.String),
    )
    op.bulk_insert(roles, [{"code": "hr", "name": "人力资源"}])
    op.bulk_insert(
        permissions, [{"code": code} for code in LEAVE_PERMISSIONS]
    )

    relations = []
    for code in ["leave.apply", "leave.view_self", "leave.cancel", "leave.modify"]:
        relations.append({"role_code": "public", "permission_code": code})
    for code in LEAVE_PERMISSIONS + [
        "kb.view_public", "kb.view_internal", "kb.manage_docs"
    ]:
        relations.append({"role_code": "hr", "permission_code": code})
    for code in LEAVE_PERMISSIONS:
        relations.append({"role_code": "admin", "permission_code": code})
    op.bulk_insert(role_permissions, relations)


def downgrade() -> None:
    op.execute("UPDATE users SET role_code='public' WHERE role_code='hr'")
    codes = ", ".join(f"'{code}'" for code in LEAVE_PERMISSIONS)
    op.execute(
        f"DELETE FROM role_permissions WHERE role_code='hr' OR permission_code IN ({codes})"
    )
    op.execute(f"DELETE FROM permissions WHERE code IN ({codes})")
    op.execute("DELETE FROM roles WHERE code='hr'")
    op.drop_table("leave_requests")