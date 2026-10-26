from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base
# 数据模型，一个数据库表对应一个类
# 为什么继承Base，闪为我们需要把我们的类注册个sqlalembic

"""表设计：
第一：先设计每个表的基本信息。
第二:设计关联表的信息"""
# 权限和角色的关系：多对多 一个角色有多钟权限，一个权限被多种角色使用
# 这是一个中间表。 之前设计中间表的方式： class role_permissions
# 在sqlalembic中用Table设计中间表，的好处是sqlalembic帮我们维护这张表
role_permissions=Table(
    "role_permissions",
    Base.metadata,
    Column("role_code",String(32),ForeignKey("roles.code",ondelete="CASCADE"),primary_key=True),
    Column("permission_code",String(64),ForeignKey("permissions.code",ondelete="CASCADE"),primary_key=True),
)

class Role(Base):
    __tablename__ = 'roles'
    code:Mapped[str]=mapped_column(String(32),primary_key=True)
    name:Mapped[str]=mapped_column(String(50),nullable=False)
    # secondary=role_permissions 通过中间表查询权限
    permissions:Mapped[list["Permission"]]=relationship(secondary=role_permissions,lazy="selectin")


class Permission(Base):
    __tablename__ = 'permissions'
    # 每个权限一个代码
    code:Mapped[str]=mapped_column(String(64),primary_key=True)

class User(Base):
    __tablename__ = 'users'
    # tinyint(-128 - 127) int(-21 > 21亿) bigint(922亿亿)
    id :Mapped[int]=mapped_column(
        mysql.BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )
    username:Mapped[str]=mapped_column(
        String(50),
        nullable=False,
    )
    email:Mapped[str]=mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )
    password_hash:Mapped[str]=mapped_column(String(250),nullable=False)
    full_name:Mapped[str]=mapped_column(String(100))
    role_code:Mapped[str]=mapped_column(String(32),ForeignKey("roles.code",ondelete="CASCADE"),default=True)
    is_active:Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(True),nullable=False,default=datetime.now)
    role:Mapped[Role]=relationship(lazy="selectin")

# 第一次初始化 Alembic 时执行：alembic init alembic