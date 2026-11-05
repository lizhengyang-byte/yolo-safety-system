"""登录认证"""
from fastapi import APIRouter, Depends, HTTPException, status

from ..config import settings
from ..schemas import LoginRequest, LoginResponse
from ..security import create_access_token

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    if (
        body.username != settings.ADMIN_USERNAME
        or body.password != settings.ADMIN_PASSWORD
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token({"sub": body.username})
    return LoginResponse(access_token=token)
