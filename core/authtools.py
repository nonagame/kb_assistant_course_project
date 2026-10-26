import os
from datetime import datetime, timezone
import jwt

from core.config import settings
from dotenv import load_dotenv
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
load_dotenv()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
class AuthHandler:
    security = HTTPBearer()
    algorithm = "HS256"
    def __init__(self):
        self.secret = JWT_SECRET_KEY
        if not self.secret:
            raise RuntimeError("没有读取到 JWT_SECRET_KEY，请检查 .env 文件")
    def _create_token(
        self,
        user_id: int,
        token_type: str,
        expires_delta,
    ) -> str:
        payload = {
            "user_id": user_id,
            "type": token_type,
            "exp": datetime.now(timezone.utc) + expires_delta,
        }
        return jwt.encode(
            payload,
            self.secret,
            algorithm=self.algorithm,
        )

    def encode_login_token(self, user_id: int) -> dict:
        return {
            "access_token": self._create_token(
                user_id=user_id,
                token_type="access",
                expires_delta=settings.JWT_ACCESS_TOKEN_EXPIRES,
            ),
            "refresh_token": self._create_token(
                user_id=user_id,
                token_type="refresh",
                expires_delta=settings.JWT_REFRESH_TOKEN_EXPIRES,
            ),
        }

    def encode_update_token(self, user_id: int) -> dict:
        return {
            "access_token": self._create_token(
                user_id=user_id,
                token_type="access",
                expires_delta=settings.JWT_ACCESS_TOKEN_EXPIRES,
            )
        }

    def _decode_token(
            self,
            token: str,
            token_type: str,
            status_code: int,
    ) -> int:
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
            )
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status_code,
                    detail="Token类型错误",
                )
            return int(payload["user_id"])
        except HTTPException:
            raise
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status_code,
                detail="Token已过期",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status_code,
                detail="Token无效",
            )
        except Exception:
            raise HTTPException(
                status_code=status_code,
                detail="Token解析失败",
            )
    def decode_access_token(self, token: str) -> int:
        return self._decode_token(
        token=token,
        token_type="access",
        status_code=HTTP_403_FORBIDDEN,
        )
    def decode_refresh_token(self, token: str) -> int:
        return self._decode_token(
        token=token,
        token_type="refresh",
        status_code=HTTP_401_UNAUTHORIZED,
        )
    def auth_access_dependency(
        self,
        auth: HTTPAuthorizationCredentials = Security(security),
        ) -> int:
        return self.decode_access_token(auth.credentials)
    def auth_refresh_dependency(
        self,
        auth: HTTPAuthorizationCredentials = Security(security),
        ) -> int:
        return self.decode_refresh_token(auth.credentials)
