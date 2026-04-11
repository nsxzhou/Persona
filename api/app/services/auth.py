# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

# 导入Python标准库时间处理模块
from datetime import UTC, datetime

# 导入FastAPI异常处理和状态码
from fastapi import HTTPException, status

# 导入异步数据库会话类型
from sqlalchemy.ext.asyncio import AsyncSession

# 导入安全相关的工具函数
from app.core.security import (
    generate_session_token,
    get_session_expiration,
    hash_password,
    hash_session_token,
    verify_password,
)

# 导入数据库模型
from app.db.models import Session, User
from app.db.repositories.auth import AuthRepository


# ==================================================
# 认证服务类 - 整个系统的安全核心
#
# 三层架构设计 - 所有现代后端都遵守这个标准：
#
# ┌─────────────┐    调用    ┌─────────────┐    调用    ┌─────────────┐
# │  Router层   │───────────▶│  Service层  │───────────▶│  Database层 │
# │ (接口路由)  │            │ (业务逻辑)  │            │   (数据库)   │
# └─────────────┘            └─────────────┘            └─────────────┘
#
# 各层职责严格划分：
# ✅ Router层：只做参数接收、参数验证、返回响应
# ✅ Service层：做所有的业务逻辑、判断、计算、安全检查
# ✅ Database层：只做数据存储和查询
#
# 绝对不允许：
# ❌ 不要在Router里写业务逻辑
# ❌ 不要在Service里返回HTTP响应
# ❌ 不要在Model里写业务逻辑
# ==================================================
class AuthService:
    def __init__(self, repository: AuthRepository | None = None) -> None:
        self.repository = repository or AuthRepository()

    # ==================================================
    # @staticmethod 说明：
    # 这个方法不需要访问类的任何属性，所以声明为静态方法
    # 前面的下划线 _ 是Python的约定：这是内部私有方法，外部代码绝对不要调用
    # ==================================================
    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        """
        时间标准化函数 - 这是后端开发第一条潜规则

        所有后端系统必须遵守的时间铁律：
        1. 永远在代码和数据库中使用UTC时间
        2. 永远不要存储本地时间
        3. 只在前端显示给用户看的最后一刻才转换成本地时间

        违反这个法则的项目最后都会遇到无法调试的时间Bug
        而且这种Bug永远在凌晨3点出现
        """
        # 如果时间没有时区信息，就强制认为是UTC
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        # 否则统一转换成UTC时间
        return value.astimezone(UTC)

    # ==================================================
    # async 关键字说明：
    # 这个函数是异步函数，调用的时候必须加 await 关键字
    # 所有涉及IO操作的函数（数据库、网络、文件）都应该是异步的
    # ==================================================
    async def is_initialized(self, session: AsyncSession) -> bool:
        """
        检查系统是否已经初始化 - 是否至少有一个用户

        参数说明：
        - self: Python类方法的强制第一个参数，永远不需要手动传，Python会自动注入
        - session: AsyncSession类型的异步数据库会话，用于执行数据库查询
        """

        return await self.repository.has_any_user(session)

    async def create_initial_admin(
        self, session: AsyncSession, username: str, password: str
    ) -> User:
        """
        创建初始管理员账号 - 只在系统第一次启动时调用

        参数说明：
        - self: Python类方法的强制第一个参数，永远不需要手动传，Python会自动注入
        - session: 异步数据库会话，用于执行数据库操作
        - username: 要创建的管理员用户名
        - password: 管理员的明文密码，会被哈希后存储
        """

        return await self.repository.create_user(
            session,
            username=username,
            password_hash=hash_password(password),
        )

    async def authenticate(
        self, session: AsyncSession, username: str, password: str
    ) -> User:
        """
        用户登录认证

        参数说明：
        - self: Python类方法的强制第一个参数，永远不需要手动传
        - session: 异步数据库会话
        - username: 用户输入的用户名
        - password: 用户输入的明文密码
        """

        user = await self.repository.get_user_by_username(session, username)

        # ==================================================
        # 🔴 安全最佳实践：
        # 无论"用户不存在"还是"密码错误"，都返回完全相同的错误信息和状态码
        #
        # 为什么？如果返回不同的错误，攻击者就可以枚举系统中存在哪些用户名
        # 这是真实世界中最常见的安全漏洞之一，几乎每个大公司都犯过这个错
        # ==================================================
        if user is None:
            # 用户不存在，也返回"账号或密码错误"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误"
            )

        if not verify_password(password, user.password_hash):
            # 密码错误，返回完全一样的错误
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误"
            )

        return user

    async def create_session(
        self, session: AsyncSession, user: User
    ) -> tuple[Session, str]:
        """
        创建用户登录会话

        参数说明：
        - self: Python类方法的强制第一个参数，永远不需要手动传
        - session: 异步数据库会话
        - user: 已经通过认证的用户对象

        返回值是一个元组：(session_record, raw_token)
        - session_record: 存储在数据库中的会话对象，里面只有哈希值
        - raw_token: 原始令牌，这个值只会在这里返回一次，永远不会存储在数据库中

        🔴 安全设计：即使整个数据库完全泄露，攻击者也无法使用任何用户的会话
        """

        # 生成256位加密安全的随机令牌
        # 这个令牌会通过Cookie发送给用户的浏览器
        raw_token = generate_session_token()

        session_record = await self.repository.create_session(
            session,
            user_id=user.id,
            token_hash=hash_session_token(raw_token),
            expires_at=get_session_expiration(),
            last_accessed_at=datetime.now(UTC),
        )

        # 这是整个系统中唯一会返回原始令牌的地方
        # 除此之外，整个系统的任何地方都不会再看到原始令牌
        return session_record, raw_token

    async def resolve_user_by_token(
        self, session: AsyncSession, raw_token: str | None
    ) -> User:
        """
        根据令牌解析用户 - 这是整个系统最核心的函数

        参数说明：
        - self: Python类方法的强制第一个参数，永远不需要手动传
        - session: 异步数据库会话
        - raw_token: 用户Cookie中携带的原始令牌

        几乎所有需要登录的接口都会先调用这个函数
        这个函数是整个认证系统的护城河
        只要这个函数没问题，整个系统的认证安全就没问题
        """

        # 第一步：令牌存在检查
        if not raw_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录"
            )

        # 第二步：计算令牌的哈希值，然后在数据库中查找
        # 数据库里存储的是哈希值，所以我们需要对用户传过来的令牌做同样的哈希
        # 注意：我们从来不会在数据库里存储原始令牌
        token_hash = hash_session_token(raw_token)
        session_record = await self.repository.get_session_by_token_hash(
            session,
            token_hash,
        )

        if session_record is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效"
            )

        # 第三步：检查会话是否过期
        expires_at = self._normalize_datetime(session_record.expires_at)
        if expires_at < datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效"
            )

        # 第四步：更新最后访问时间
        # 每次用户访问都更新这个时间，可以用来判断用户活跃状态
        session_record.last_accessed_at = datetime.now(UTC)
        await self.repository.flush(session)

        # 第五步：查询关联的用户对象
        user = await self.repository.get_user_by_id(session, session_record.user_id)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录"
            )

        return user

    async def delete_session(
        self, session: AsyncSession, raw_token: str | None
    ) -> None:
        """用户登出 - 删除会话"""

        if not raw_token:
            return

        await self.repository.delete_session_by_token_hash(
            session,
            hash_session_token(raw_token),
        )

    async def delete_account(self, session: AsyncSession) -> None:
        """删除所有账号数据"""
        await self.repository.delete_all_account_data(session)
