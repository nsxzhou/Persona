# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

# 导入Python标准库模块
import uuid
from datetime import UTC, datetime

# 导入SQLAlchemy字段类型
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func

# 导入SQLAlchemy 2.0的新ORM API
# Mapped: 类型注解包装器，用于声明模型字段
# mapped_column: 用于配置字段的数据库映射
# relationship: 用于定义表之间的关联关系
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 导入数据库基类
from app.db.base import Base


# UUID生成函数
# 生成符合RFC 4122标准的UUID v4，作为数据库表的主键
# 这是现代后端的最佳实践，比自增ID更安全、更适合分布式系统
def generate_uuid() -> str:
    return str(uuid.uuid4())


# 时间戳混入类
# 这是Python的Mixin设计模式：所有需要创建时间和更新时间的模型都可以继承这个类
# 不需要在每个模型里重复写这两个字段
#
# 所有字段同时设置了server_default和default：
# - server_default: 数据库层面的默认值，直接插入SQL时生效
# - default: Python层面的默认值，内存中创建对象时生效
# 双重保险，确保无论通过什么方式创建记录，时间都是正确的
class TimestampMixin:
    # 记录创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # 使用带时区的时间类型
        nullable=False,  # 不允许为空
        server_default=func.now(),  # 数据库层面的默认值，使用数据库的当前时间
        default=lambda: datetime.now(UTC),  # Python层面的默认值，使用UTC时间
    )
    # 记录更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),  # 更新记录时自动更新这个时间
    )


# 用户表模型
# 所有数据库模型都要继承：
# 1. 想要的Mixin类（如TimestampMixin）
# 2. 基类Base
class User(TimestampMixin, Base):
    # 数据库表名 - 数据库表名总是用复数形式，这是约定俗成
    __tablename__ = "users"

    # 用户ID主键 - UUID字符串，长度36字符
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    # 用户名 - 唯一索引，不允许重复
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # 密码哈希值 - 永远不要存储明文密码！这里存储的是Argon2哈希后的结果
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # 关联关系：一个用户有多个会话
    # back_populates: 双向关联，和Session类中的user字段对应
    # cascade="all, delete-orphan": 删除用户时自动删除所有关联的会话
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# 会话表模型
# 存储用户的登录会话信息
class Session(TimestampMixin, Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    # 外键关联到用户表
    # ondelete="CASCADE": 删除用户时自动删除该用户的所有会话
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # 会话令牌哈希值 - 注意存储的是HMAC哈希后的值，不是原始令牌
    # index=True: 加索引，因为查询会话时会频繁通过这个字段查询
    token_hash: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    # 会话过期时间
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # 最后访问时间 - 用于判断会话是否活跃
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # 反向关联：一个会话属于一个用户
    user: Mapped["User"] = relationship(back_populates="sessions")


# 提供商配置表模型
# 存储LLM提供商（OpenAI、Anthropic等）的配置信息
class ProviderConfig(TimestampMixin, Base):
    __tablename__ = "provider_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    # 配置标签，给用户看的名字
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    # API端点地址
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    # 加密后的API密钥 - 这里存储的是AES-GCM加密后的值，不是明文
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    # API密钥后四位提示 - 用于界面显示，让用户认出自己用的是哪个密钥
    api_key_hint_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    # 默认使用的模型
    default_model: Mapped[str] = mapped_column(String(100), nullable=False)
    # 是否启用这个配置
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 上次测试状态
    last_test_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 上次测试错误信息
    last_test_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 上次测试时间
    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 关联关系：一个提供商配置可以被多个项目使用
    projects: Mapped[list["Project"]] = relationship(back_populates="provider")
    # 关联关系：一个提供商配置可以创建多个风格分析任务
    style_analysis_jobs: Mapped[list["StyleAnalysisJob"]] = relationship(
        back_populates="provider"
    )
    style_profiles: Mapped[list["StyleProfile"]] = relationship(
        back_populates="provider"
    )


# 项目表模型
# 存储用户创建的项目信息
class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    # 项目名称
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # 项目描述
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 项目状态：draft/active/paused
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    # 外键关联到提供商配置
    default_provider_id: Mapped[str] = mapped_column(
        ForeignKey("provider_configs.id"), nullable=False
    )
    # 默认使用的模型
    default_model: Mapped[str] = mapped_column(String(100), nullable=False)
    # 风格配置ID - 可选
    style_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("style_profiles.id"), nullable=True
    )
    # 归档时间 - 如果归档了就有值，否则是None
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 反向关联：一个项目属于一个提供商配置
    provider: Mapped["ProviderConfig"] = relationship(back_populates="projects")
    style_profile: Mapped["StyleProfile | None"] = relationship(back_populates="projects")


class StyleSampleFile(TimestampMixin, Base):
    __tablename__ = "style_sample_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    character_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    job: Mapped["StyleAnalysisJob"] = relationship(back_populates="sample_file")


class StyleAnalysisJob(TimestampMixin, Base):
    __tablename__ = "style_analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    style_name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_id: Mapped[str] = mapped_column(
        ForeignKey("provider_configs.id"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sample_file_id: Mapped[str] = mapped_column(
        ForeignKey("style_sample_files.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analysis_meta_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analysis_report_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    style_summary_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prompt_pack_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    provider: Mapped["ProviderConfig"] = relationship(back_populates="style_analysis_jobs")
    sample_file: Mapped["StyleSampleFile"] = relationship(
        back_populates="job", single_parent=True
    )
    style_profile: Mapped["StyleProfile | None"] = relationship(back_populates="source_job")


class StyleProfile(TimestampMixin, Base):
    __tablename__ = "style_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_job_id: Mapped[str] = mapped_column(
        ForeignKey("style_analysis_jobs.id"), nullable=False, unique=True
    )
    provider_id: Mapped[str] = mapped_column(
        ForeignKey("provider_configs.id"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    style_name: Mapped[str] = mapped_column(String(120), nullable=False)
    analysis_summary: Mapped[str] = mapped_column(Text, nullable=False)
    global_system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSON, nullable=False)
    scene_prompts: Mapped[dict] = mapped_column(JSON, nullable=False)
    few_shot_examples: Mapped[list] = mapped_column(JSON, nullable=False)
    analysis_report_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    style_summary_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prompt_pack_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    source_job: Mapped["StyleAnalysisJob"] = relationship(back_populates="style_profile")
    provider: Mapped["ProviderConfig"] = relationship(back_populates="style_profiles")
    projects: Mapped[list["Project"]] = relationship(back_populates="style_profile")
