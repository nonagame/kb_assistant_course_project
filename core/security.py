from pwdlib import PasswordHash

from core.config import settings

password_hash = PasswordHash.recommended()
print(password_hash)
def hash_password(password):
    return password_hash.hash(password)
def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


import jwt
from datetime import datetime, timedelta, timezone
# 创建token
def _create_token(
    user_id: int,
    role: str,
    token_type: str,
    expires_at: datetime,
) -> str:
    return jwt.encode(
        {"sub": str(user_id), "role": role, "type": token_type, "exp": expires_at},
        settings.jwt_secret_key,
        algorithm="HS256",
    )

# 创建access和refresh_token
def create_token_pair(user_id:int,role:str)->tuple[str,str]:
    now=datetime.now()
    access_token=_create_token(
        user_id,
        role,
        "access",
        now+timedelta(minutes=settings.access_token_minutes)
    )
    refresh_token=_create_token(
        user_id,
        role,
        "refresh",
        now+timedelta(minutes=settings.refresh_token_minutes)
    )
# 创建access和refresh_token
def create_token_pair(user_id: int, role: str) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    access_token = _create_token(
        user_id,
        role,
        "access",
        now + timedelta(minutes=settings.access_token_minutes),
    )
    refresh_token = _create_token(
        user_id,
        role,
        "refresh",
        now + timedelta(days=settings.refresh_token_days),
    )
    return access_token, refresh_token

# 解析token
def _decode_token(token: str, expected_type: str) -> tuple[int, str]:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Token 类型错误")
    return int(payload["sub"]), str(payload["role"])

# 解析访问token
def decode_access_token(token: str) -> tuple[int, str]:
    return _decode_token(token, "access")

def decode_refresh_token(token: str) -> tuple[int, str]:
    return _decode_token(token, "refresh")