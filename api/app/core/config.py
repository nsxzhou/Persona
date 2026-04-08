# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

# 导入LRU缓存装饰器 - 用于缓存函数返回值，避免重复计算
from functools import lru_cache

# 导入Pydantic库组件
# Pydantic是Python最流行的数据验证库，FastAPI内置了对它的完整支持
from pydantic import Field

# BaseSettings: 专门用于处理配置设置的基类，能自动从环境变量读取配置
# SettingsConfigDict: 配置类的配置选项
from pydantic_settings import BaseSettings, SettingsConfigDict


# 应用配置类 - 所有配置项都在这里定义
# 继承自BaseSettings意味着这个类会自动：
# 1. 从环境变量读取配置
# 2. 从.env文件读取配置
# 3. 自动做类型转换和验证
class Settings(BaseSettings):
    # 数据库连接URL
    # 格式说明: 数据库类型+驱动://用户名:密码@主机:端口/数据库名
    # default: 默认值，本地开发时使用
    # alias: 环境变量名称，部署时会读取这个环境变量的值
    database_url: str = Field(
        default="postgresql+asyncpg://persona:persona@localhost:5432/persona",
        alias="PERSONA_DATABASE_URL",
    )

    # 加密密钥 - 用于加密敏感数据，必须通过环境变量设置
    # 注意：这个字段没有默认值，启动时必须设置PERSONA_ENCRYPTION_KEY环境变量
    encryption_key: str = Field(alias="PERSONA_ENCRYPTION_KEY")

    # Session Cookie名称 - 存储在用户浏览器中的Cookie名字
    session_cookie_name: str = Field(
        default="persona_session", alias="PERSONA_SESSION_COOKIE_NAME"
    )

    # Session Cookie安全标记 - True表示只能通过HTTPS传输
    session_cookie_secure: bool = Field(
        default=True, alias="PERSONA_SESSION_COOKIE_SECURE"
    )

    # Session有效期 - 单位小时，默认14天(24*14)
    session_ttl_hours: int = Field(default=24 * 14, alias="PERSONA_SESSION_TTL_HOURS")

    # Session加密密钥 - 可选，不设置会自动生成
    # str | None 表示可以是字符串或者None(空值)
    session_secret: str | None = Field(default=None, alias="PERSONA_SESSION_SECRET")

    # CORS允许的源列表 - 哪些域名可以访问API
    # default_factory: 当默认值需要动态生成时使用，这里生成一个列表
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        alias="PERSONA_CORS_ALLOWED_ORIGINS",
    )

    # LLM调用超时时间 - 单位秒，调用大语言模型的超时时间
    llm_timeout_seconds: float = Field(
        default=15.0, alias="PERSONA_LLM_TIMEOUT_SECONDS"
    )

    # LLM最大重试次数 - 调用失败时最多重试几次
    llm_max_retries: int = Field(default=2, alias="PERSONA_LLM_MAX_RETRIES")

    # Pydantic配置 - 定义Settings类本身的行为
    model_config = SettingsConfigDict(
        # 从.env文件读取配置 - 开发环境会用这个文件
        env_file=".env",
        # .env文件的编码格式
        env_file_encoding="utf-8",
        # 忽略额外的环境变量 - 不会因为有未定义的环境变量而报错
        extra="ignore",
    )


# 获取配置实例的函数
# @lru_cache是Python的装饰器，作用是：
# 1. 第一次调用这个函数时，执行函数体，创建Settings实例
# 2. 之后所有调用直接返回缓存的实例，不会重复创建
# 3. 这是单例模式的Python实现方式，确保整个应用只有一个配置实例
@lru_cache
def get_settings() -> Settings:
    # 创建并返回Settings实例
    return Settings()
