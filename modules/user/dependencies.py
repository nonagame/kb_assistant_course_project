# 这个文件一般写依赖注入的一些函数

"""查询当前用户  通过token访问的格式如下：Authorization: Bearer
GET http://127.0.0.1:8000/auth/me
Authorization: Bearer eyJhbGciOiJIUzI...
"""
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.security import decode_access_token
from database.connection import get_session
from modules.user.repository import get_perssion, get_user_by_id
from modules.user.schemas import CurrentUser

# 创建一个“BearerToken 解析器”。它会去请求头里找
# Authorization: Bearer eyJhbGci0iJIUzI1NiIs...

# 这个对象是fastapi专门用来接收tokn的一个对象
bearer = HTTPBearer(auto_error=False)

# HTTPAuthorizationCredentials(
#    scheme="Bearer",
#    credentials="eyJhbGciOiJIUzI1NiIs..."
# )
from modules.user.model import User
def get_current_user(
        # 注入token
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
        # 注入session
    db: Annotated[Session, Depends(get_session)],
):
    # 加一层防御（虽然OAuth2PasswordBearer理论上不会返回None，
    # 但某些边界情况如 malformed header 会导致 credentials=None）
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 如果获取token，用该是credentials.credentials
    # 根据token解析出用户的id
    user_id, token_role = decode_access_token(credentials.credentials)
    user:User = get_user_by_id(db, user_id)
    return  CurrentUser(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name,
        permissions=get_perssion(db,int(user.id))
    )
