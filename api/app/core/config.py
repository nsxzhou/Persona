# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

# 导入LRU缓存装饰器 - 用于缓存函数返回值，避免重复计算
from functools import lru_cache

# 导入Pydantic库组件
# Pydantic是Python最流行的数据验证库，FastAPI内置了对它的完整支持
from pydantic import Field, model_validator

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
    encryption_key: str = Field(default="", alias="PERSONA_ENCRYPTION_KEY")

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
        default=180.0, alias="PERSONA_LLM_TIMEOUT_SECONDS"
    )

    # LLM最大重试次数 - 调用失败时最多重试几次
    llm_max_retries: int = Field(default=2, alias="PERSONA_LLM_MAX_RETRIES")

    # 本地文件存储目录：保存 Style Lab 原始 TXT 样本
    storage_dir: str = Field(default="./storage", alias="PERSONA_STORAGE_DIR")

    style_analysis_max_upload_bytes: int = Field(
        default=20 * 1024 * 1024,
        alias="PERSONA_STYLE_ANALYSIS_MAX_UPLOAD_BYTES",
    )

    # Style Lab 后台 worker 开关：测试环境可关闭，避免引入不必要的并发噪音
    style_analysis_worker_enabled: bool = Field(
        default=True, alias="PERSONA_STYLE_ANALYSIS_WORKER_ENABLED"
    )

    # worker 轮询间隔（秒）
    style_analysis_poll_interval_seconds: float = Field(
        default=1.0,
        gt=0,
        le=60,
        alias="PERSONA_STYLE_ANALYSIS_POLL_INTERVAL_SECONDS",
    )

    # 运行中任务的陈旧判定阈值（秒）
    style_analysis_stale_timeout_seconds: int = Field(
        default=300, alias="PERSONA_STYLE_ANALYSIS_STALE_TIMEOUT_SECONDS"
    )

    # 用户请求暂停后，若 worker 没有继续 heartbeat，多久后自动确认暂停
    analysis_pause_confirm_timeout_seconds: int = Field(
        default=10,
        ge=1,
        le=120,
        alias="PERSONA_ANALYSIS_PAUSE_CONFIRM_TIMEOUT_SECONDS",
    )

    # Style Lab chunk 并发上限
    style_analysis_chunk_max_concurrency: int = Field(
        default=5,
        ge=1,
        le=32,
        alias="PERSONA_STYLE_ANALYSIS_CHUNK_MAX_CONCURRENCY",
    )

    # Style Lab 最大尝试次数
    style_analysis_max_attempts: int = Field(
        default=3, alias="PERSONA_STYLE_ANALYSIS_MAX_ATTEMPTS"
    )

    # Style Lab LangGraph checkpoint 连接串，可覆盖数据库推导逻辑
    style_analysis_checkpoint_url: str | None = Field(
        default=None, alias="PERSONA_STYLE_ANALYSIS_CHECKPOINT_URL"
    )

    # Pydantic配置 - 定义Settings类本身的行为
    model_config = SettingsConfigDict(
        # 从.env文件读取配置 - 开发环境会用这个文件
        env_file=".env",
        # .env文件的编码格式
        env_file_encoding="utf-8",
        # 忽略额外的环境变量 - 不会因为有未定义的环境变量而报错
        extra="ignore",
    )

    @model_validator(mode="after")
    def _validate_encryption_key(self) -> Settings:
        if not self.encryption_key.strip():
            raise ValueError(
                "缺少加密密钥：请设置环境变量 PERSONA_ENCRYPTION_KEY（或在 .env 中设置）。"
                "开发环境可先设置为任意随机字符串（建议长度≥32）；生产环境必须使用强随机值。"
            )
        return self


# 获取配置实例的函数
# @lru_cache是Python的装饰器，作用是：
# 1. 第一次调用这个函数时，执行函数体，创建Settings实例
# 2. 之后所有调用直接返回缓存的实例，不会重复创建
# 3. 这是单例模式的Python实现方式，确保整个应用只有一个配置实例
@lru_cache
def get_settings() -> Settings:
    # 创建并返回Settings实例
    return Settings()
