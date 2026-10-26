"""管理权限"""

from collections.abc import Callable
from fastapi import Depends, HTTPException, status
from modules.user.dependencies import get_current_user
from modules.user.schemas import CurrentUser

# 接口检查
def require_permission(permission: str) -> Callable:
    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if permission not in user.permissions:
            raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"缺少权限：{permission}",
            )
        return user
    return checker

# 检索在服务端计算范围
def allowed_visibilities(user: CurrentUser) -> list[str]:
    allowed = ["public"]
    if "kb.view_internal" in user.permissions or "kb.manage_docs" in user.permissions:
        allowed.append("internal")
    return allowed
