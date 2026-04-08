# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

# 导入Python标准库时间处理模块
from datetime import UTC, datetime

# 导入FastAPI异常处理和状态码
from fastapi import HTTPException, status

# 导入SQLAlchemy查询构造器
from sqlalchemy import delete, select

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

        # select(User.id).limit(1) 是查询"是否存在"的最优化写法
        # 为什么不写 select(User)？因为不需要查询整个对象，只需要判断有没有
        # 为什么加limit(1)？因为找到第一个就可以停止查询了，不用扫描整个表
        # 这条查询的速度永远是O(1)，不会随着用户数量增加而变慢
        query = select(User.id).limit(1)

        # ==================================================
        # await 关键字说明：
        # 在这里暂停当前函数的执行，让CPU去处理其他请求
        # 等数据库返回结果之后，再回来继续执行后面的代码
        # 这就是异步IO的核心：不等待，不阻塞
        # ==================================================
        result = await session.scalar(query)

        # 如果结果不是None，说明至少有一个用户存在
        return result is not None

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

        # 创建用户对象
        # 🔴 安全原则第一条：永远不要在数据库中存储明文密码
        # hash_password 返回的是Argon2哈希值，这个值是单向的，数学上无法反推出原始密码
        # 即使数据库完全泄露，攻击者也无法得到用户的密码
        user = User(username=username, password_hash=hash_password(password))

        # 将对象添加到会话中
        # 注意：此时还没有发送任何SQL到数据库，只是在内存中标记了这个对象要被插入
        session.add(user)

        # ==================================================
        # flush() 和 commit() 的本质区别：
        #
        # flush()  → 把SQL发送到数据库执行，但是事务还没有提交
        #            执行后对象就有id了，但是出错了还可以回滚
        #
        # commit() → 提交事务，所有修改永久写入磁盘，无法回滚
        #
        # Service层永远只调用flush()，永远不要调用commit()
        # commit()应该在最外层的依赖注入中统一处理
        # ==================================================
        await session.flush()

        return user

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

        # 通过用户名查询用户
        # where(User.username == username) 生成参数化查询，防止SQL注入
        query = select(User).where(User.username == username)
        user = await session.scalar(query)

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

        # 创建数据库中的会话记录
        session_record = Session(
            user_id=user.id,
            # 🔴 数据库中只存储HMAC哈希后的令牌，不存储原始令牌
            # 即使数据库被盗，攻击者也无法伪造有效会话
            # 这就是为什么你从来没听过这个系统的用户会话被窃取的新闻
            token_hash=hash_session_token(raw_token),
            # 会话过期时间
            expires_at=get_session_expiration(),
            # 最后访问时间
            last_accessed_at=datetime.now(UTC),
        )

        session.add(session_record)
        await session.flush()

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
        query = select(Session).where(Session.token_hash == token_hash)
        session_record = await session.scalar(query)

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
        await session.flush()

        # 第五步：查询关联的用户对象
        # session.get() 是SQLAlchemy根据主键查询的最快方法
        # 会自动使用缓存，不会重复查询
        user = await session.get(User, session_record.user_id)

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

        # 计算令牌哈希，然后删除对应的会话记录
        token_hash = hash_session_token(raw_token)
        query = delete(Session).where(Session.token_hash == token_hash)

        # execute() 用于执行不返回结果的查询（DELETE/UPDATE等）
        await session.execute(query)
