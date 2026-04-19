from fastapi import APIRouter, HTTPException, Response, status
from passlib.context import CryptContext

from app.config import settings
from app.dependencies import create_access_token
from app.schemas import LoginRequest

router = APIRouter()

_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
_HASHED_DEMO_PASSWORD = _pwd.hash(settings.demo_password)

_DEMO_USER = {
    "username": settings.demo_username,
    "role": "ADMIN",
}

_COOKIE_NAME = "access_token"
_COOKIE_MAX_AGE = 60 * 60 * 8  # 8 hours


@router.post("/auth/login", status_code=status.HTTP_200_OK)
async def login(body: LoginRequest, response: Response):
    if body.username != _DEMO_USER["username"] or not _pwd.verify(body.password, _HASHED_DEMO_PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "아이디 또는 비밀번호가 올바르지 않습니다"},
        )
    token = create_access_token({"sub": _DEMO_USER["username"], "role": _DEMO_USER["role"]})
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="none" if settings.cookie_secure else "lax",
        secure=settings.cookie_secure,
        max_age=_COOKIE_MAX_AGE,
        path="/",
    )
    return {"ok": True}


@router.post("/auth/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    response.delete_cookie(key=_COOKIE_NAME, path="/")
    return {"ok": True}
