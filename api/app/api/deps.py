# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

# 导入FastAPI依赖注入系统
# Depends是FastAPI最强大也是最独特的功能
from fastapi import Depends, Request

# 导入异步数据库会话类型
from sqlalchemy.ext.asyncio import AsyncSession

# 导入项目组件
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db_session
from app.services.auth import AuthService


# ==================================================
# FastAPI依赖注入系统的魔法
#
# 这个函数是整个项目最核心的依赖，没有之一
# 所有需要登录的接口只需要写一行：
# current_user: User = Depends(get_current_user)
#
# 不需要在每个接口里重复写认证逻辑
# FastAPI会自动帮你完成所有的认证工作
# ==================================================
async def get_current_user(
    # 📝 参数1: request
    # 这个是FastAPI自动传给你的，不需要你做任何事
    # 每个请求都会有一个新的request对象
    request: Request,
    # 📝 参数2: db_session
    # ✨ 依赖的依赖
    # get_current_user 自己也是一个依赖，它还可以依赖其他依赖
    # FastAPI会自动先调用 get_db_session 创建会话
    # 然后把创建好的会话放到这个参数里
    # 这就叫"依赖注入树"，可以无限嵌套
    db_session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    获取当前登录用户 - FastAPI依赖注入

    ✅ 这是FastAPI最强大的特性：依赖注入系统
    只要接口参数里写了 current_user: User = Depends(get_current_user)
    FastAPI会自动：
    1. 调用get_db_session获取数据库会话
    2. 调用这个get_current_user函数
    3. 自动处理所有的认证和错误
    4. 如果认证失败，接口甚至都不会被执行
    """
    # 获取配置
    settings = get_settings()
    # 创建认证服务
    auth_service = AuthService()
    # 从Cookie中获取会话令牌，然后解析用户
    return await auth_service.resolve_user_by_token(
        db_session,
        # 从用户的Cookie中读取会话令牌
        request.cookies.get(settings.session_cookie_name),
    )
