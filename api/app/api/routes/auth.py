# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, set_session_cookie
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.auth import LoginRequest, UserResponse
from app.services.auth import AuthService

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=UserResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db_session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """用户登录接口"""
    auth_service = AuthService()
    if not await auth_service.is_initialized(db_session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="系统尚未初始化"
        )
    user = await auth_service.authenticate(
        db_session, payload.username, payload.password
    )
    _, raw_token = await auth_service.create_session(db_session, user)

    set_session_cookie(response, raw_token)

    return UserResponse.model_validate(user)


# 登出接口
# status_code=204: 表示操作成功但是没有返回内容
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    """用户登出接口"""
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    await AuthService().delete_session(db_session, raw_token)

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.session_cookie_name, path="/")

    return response


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    response: Response,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """删除当前用户账号，清除所有数据"""
    await AuthService().delete_account(db_session)

    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name, path="/")


# 获取当前用户信息接口
@router.get("/me", response_model=UserResponse)
async def me(
    # 这就是依赖注入的魔力！
    # 只要写这一行，这个接口就自动需要登录
    # FastAPI会自动完成所有认证工作
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """获取当前登录用户信息"""

    # 把数据库对象转换成API响应对象
    return UserResponse.model_validate(current_user)
