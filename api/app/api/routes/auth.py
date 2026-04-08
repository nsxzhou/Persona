# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

# 导入FastAPI核心组件
# APIRouter: 路由分组器，用于把相关的接口组织在一起
# Depends: 依赖注入系统
# HTTPException: HTTP异常
# Request/Response: HTTP请求和响应对象
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

# 导入SQLAlchemy查询构造器
from sqlalchemy import delete

# 导入异步数据库会话类型
from sqlalchemy.ext.asyncio import AsyncSession

# 导入依赖
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.models import Project, ProviderConfig, Session, User
from app.db.session import get_db_session

# 导入Schema
from app.schemas.auth import LoginRequest, UserResponse

# 导入服务
from app.services.auth import AuthService

# 创建认证路由分组
# tags=["auth"] 会在自动生成的OpenAPI文档中把这些接口归到auth分类下
router = APIRouter(tags=["auth"])


# 内部工具函数：设置会话Cookie
# 开头的下划线表示这是内部函数，外部不应该直接调用
def _set_session_cookie(response: Response, raw_token: str) -> None:
    """
    设置安全的会话Cookie

    这里的每一个参数都是安全最佳实践：
    - httponly: JavaScript无法读取这个Cookie，防止XSS攻击窃取会话
    - secure: 只能通过HTTPS传输，防止中间人攻击
    - samesite: 防止CSRF攻击
    - max_age: Cookie过期时间，和会话过期时间一致
    """
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        httponly=True,  # 🔴 最重要的安全选项，禁止JS读取
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,  # 转换成秒
        path="/",
    )


# ==================================================
# 登录接口
# @router.post: 这是POST请求
# response_model=UserResponse: 自动把返回值序列化成UserResponse的格式
# ==================================================
@router.post("/login", response_model=UserResponse)
async def login(
    # 📝 参数1: payload
    # 这个参数是用户从前端发过来的JSON数据
    # FastAPI会自动：
    # 1. 检查用户有没有发JSON
    # 2. 检查JSON里有没有username和password字段
    # 3. 检查长度是不是符合要求
    # 4. 如果有任何问题，直接返回422错误，根本不会执行这个函数
    payload: LoginRequest,
    # 📝 参数2: response
    # 这个对象是FastAPI自动传给你的
    # 你可以用它来设置Cookie、设置响应头等
    # 你不需要创建它，FastAPI会自动给你准备好
    response: Response,
    # 📝 参数3: db_session
    # ✨ 这是FastAPI最神奇的魔法：依赖注入
    # 你只要在这里写: db_session: AsyncSession = Depends(get_db_session)
    # FastAPI就会自动：
    # 1. 调用get_db_session()函数
    # 2. 把返回的数据库会话放到这个参数里
    # 3. 请求结束后自动关闭会话
    # 你什么都不用管，直接用就行
    db_session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """用户登录接口"""

    auth_service = AuthService()

    # 第一步：检查系统是否已经初始化
    if not await auth_service.is_initialized(db_session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="系统尚未初始化"
        )

    # 第二步：认证用户名和密码
    user = await auth_service.authenticate(
        db_session, payload.username, payload.password
    )

    # 第三步：创建会话
    _, raw_token = await auth_service.create_session(db_session, user)

    # ==================================================
    # 🔴 唯一的commit()调用
    #
    # Router层是唯一应该调用commit()的地方
    # Service层永远只调用flush()
    # 这是三层架构最重要的规则之一
    # ==================================================
    await db_session.commit()

    # 第四步：设置Cookie
    _set_session_cookie(response, raw_token)

    # 第五步：返回用户信息
    # model_validate: 把数据库ORM对象转换成API响应对象
    return UserResponse.model_validate(user)


# 登出接口
# status_code=204: 表示操作成功但是没有返回内容
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    # 📝 参数1: request
    # FastAPI自动传给你的请求对象
    # 里面包含了用户的Cookie、请求头、IP地址等所有请求相关的信息
    request: Request,
    # 📝 参数2: db_session
    # 和上面一样，自动注入的数据库会话
    db_session: AsyncSession = Depends(get_db_session),
    # 📝 参数3: current_user
    # ✨ 这是最能体现FastAPI威力的地方
    # 只要你写: current_user: User = Depends(get_current_user)
    #
    # FastAPI就会自动帮你做这些事：
    # 1. 从Cookie里读令牌
    # 2. 去数据库查这个令牌是否有效
    # 3. 检查有没有过期
    # 4. 如果有任何问题直接返回401错误
    # 5. 只有所有检查都通过了，才会执行你这个函数里的代码
    #
    # 整个系统里几百个接口，都只要写这一行，不需要复制粘贴任何代码
    current_user: User = Depends(get_current_user),
) -> Response:
    """用户登出接口"""

    # del current_user 是一个小技巧：告诉linter这个变量我们故意不用
    del current_user

    settings = get_settings()
    # 从Cookie中获取令牌
    raw_token = request.cookies.get(settings.session_cookie_name)

    # 删除数据库中的会话
    await AuthService().delete_session(db_session, raw_token)

    # 提交事务
    await db_session.commit()

    # 创建响应并删除Cookie
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.session_cookie_name, path="/")

    return response


# 删除账号接口
@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    response: Response,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """删除当前用户账号，清除所有数据"""

    # 删除所有数据 - 注意这是演示项目的简单实现
    # 生产环境应该只删除当前用户的相关数据
    await db_session.execute(delete(Project))
    await db_session.execute(delete(ProviderConfig))
    await db_session.execute(delete(Session))
    await db_session.execute(delete(User))

    await db_session.commit()

    # 删除Cookie
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
