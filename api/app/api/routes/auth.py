# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.deps import AuthServiceDep, CurrentUserDep, DbSessionDep, set_session_cookie
from app.core.config import get_settings
from app.core.domain_errors import DomainError, to_http_exception
from app.schemas.auth import LoginRequest, UserResponse

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=UserResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db_session: DbSessionDep,
    auth_service: AuthServiceDep,
) -> UserResponse:
    """用户登录接口"""
    try:
        await auth_service.ensure_initialized(db_session)
        user = await auth_service.authenticate(
            db_session, payload.username, payload.password
        )
        _, raw_token = await auth_service.create_session(db_session, user)
    except DomainError as exc:
        raise to_http_exception(exc) from exc

    set_session_cookie(response, raw_token)

    return UserResponse.model_validate(user)


# 登出接口
# status_code=204: 表示操作成功但是没有返回内容
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    db_session: DbSessionDep,
    _current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
) -> Response:
    """用户登出接口"""
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    await auth_service.delete_session(db_session, raw_token)

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.session_cookie_name, path="/")

    return response


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    response: Response,
    db_session: DbSessionDep,
    _current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
) -> None:
    """删除当前用户账号，清除所有数据"""
    await auth_service.delete_account(db_session)

    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name, path="/")


# 获取当前用户信息接口
@router.get("/me", response_model=UserResponse)
async def me(
    # 这就是依赖注入的魔力！
    # 只要写这一行，这个接口就自动需要登录
    # FastAPI会自动完成所有认证工作
    current_user: CurrentUserDep,
) -> UserResponse:
    """获取当前登录用户信息"""

    # 把数据库对象转换成API响应对象
    return UserResponse.model_validate(current_user)
