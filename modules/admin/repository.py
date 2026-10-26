from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session
from modules.user.model import Permission, Role, User, role_permissions

# 查询角色
def list_roles(db: Session) -> list[Role]:
    return list(db.scalars(select(Role).order_by(Role.code)).all())

# 查询权限字典
def list_permissions(db: Session) -> list[str]:
    return list(db.scalars(select(Permission.code).order_by(Permission.code)).all())

# 角色查询
def get_role(db: Session, role_code: str) -> Role | None:
    return db.get(Role, role_code)

# 权限检查
def permission_codes_exist(db: Session, codes: set[str]) -> bool:
    if not codes:
        return True
    found =set(db.scalars(select(Permission.code).where(Permission.code.in_(codes))).all())
    return found == codes

# 关系替换
def replace_role_permissions(db: Session, role_code: str, codes: set[str]) ->None:
    # 删除该角色的所有的权限
    db.execute(delete(role_permissions).where(role_permissions.c.role_code ==role_code))
    # 把你想赋值的权限挨个插入数据库
    if codes:
        # fastapi批量操作数据
        db.execute(
            insert(role_permissions),
            [{"role_code": role_code, "permission_code": code} for code in sorted(codes)],
        )

# 更新用户角色
def set_user_role(db:Session,user_id:int,role_code:str) ->User |None:
    user=db.get(User,user_id)
    if user is None:
        return None
    user.role_code=role_code
    db.flush()
    return user

