from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.connection import get_session
from modules.admin import service
from modules.admin.schemas import RoleOut, RolePermissionsIn, UserRoleIn,UserRoleOut
from modules.user.permissions import require_permission
from modules.user.schemas import CurrentUser

router = APIRouter(prefix="/admin", tags=["系统管理"])

# A1：查询角色及其权限
@router.get("/roles", response_model=list[RoleOut])
def roles(db: Session = Depends(get_session),
          _: CurrentUser = Depends(require_permission("system.manage_roles")),
          ) -> list[RoleOut]:
    return service.get_roles(db)

# A2：查询全部权限码
@router.get("/permissions", response_model=list[str])
def permissions(
    db: Session = Depends(get_session),
    _: CurrentUser = Depends(require_permission("system.manage_roles")),
) -> list[str]:
    return service.get_permissions(db)

# A3：修改角色权限 获取角色、获取权限
@router.put("/roles/{role_code}/permissions", response_model=RoleOut)
def update_role_permissions(
    role_code: str,
    data: RolePermissionsIn,
    db: Session = Depends(get_session),
    _: CurrentUser = Depends(require_permission("system.manage_roles")),
) -> RoleOut:
    return service.set_role_permissions(db, role_code, data.permission_codes)

# A4：设置用户角色
@router.put("/users/{user_id}/role",response_model=UserRoleOut)
def update_user_role(
        user_id: int,
        data: UserRoleIn,
        db: Session = Depends(get_session),
        _: CurrentUser = Depends(require_permission("system.manage_users")),
)->UserRoleOut:
    return service.set_user_role(db, user_id, data.role_code)



