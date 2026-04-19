from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

_ALGORITHM = "HS256"
_EXPIRE_MINUTES = 480  # 8 hours

_bearer = HTTPBearer(auto_error=False)


def create_access_token(data: dict) -> str:
    payload = {**data, "exp": datetime.now(timezone.utc) + timedelta(minutes=_EXPIRE_MINUTES)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "유효하지 않은 인증 토큰"},
        )


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    # Cookie takes priority; Bearer fallback for API clients / tests
    token = access_token or (credentials.credentials if credentials else None)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "인증 토큰이 필요합니다"},
        )
    return _decode_token(token)


require_auth = get_current_user
