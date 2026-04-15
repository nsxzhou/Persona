# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

# 导入Python标准库模块
import uuid
from datetime import UTC, datetime

# 导入SQLAlchemy字段类型
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)

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
    provider_configs: Mapped[list["ProviderConfig"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    style_sample_files: Mapped[list["StyleSampleFile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    style_analysis_jobs: Mapped[list["StyleAnalysisJob"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    style_profiles: Mapped[list["StyleProfile"]] = relationship(
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
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
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
    user: Mapped["User"] = relationship(back_populates="provider_configs")

    @property
    def api_key_hint(self) -> str:
        return f"****{self.api_key_hint_last4}"


# 项目表模型
# 存储用户创建的项目信息
class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 项目名称
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # 项目描述
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 项目状态：draft/active/paused
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    # 外键关联到提供商配置
    default_provider_id: Mapped[str] = mapped_column(
        ForeignKey("provider_configs.id"), nullable=False, index=True
    )
    # 默认使用的模型
    default_model: Mapped[str] = mapped_column(String(100), nullable=False)
    # 风格配置ID - 可选
    style_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("style_profiles.id"), nullable=True, index=True
    )
    # 故事圣经各区块
    inspiration: Mapped[str] = mapped_column(Text, nullable=False, default="")
    world_building: Mapped[str] = mapped_column(Text, nullable=False, default="")
    characters: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outline_master: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outline_detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    story_bible: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 项目正文内容
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 归档时间 - 如果归档了就有值，否则是None
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 反向关联：一个项目属于一个提供商配置
    provider: Mapped["ProviderConfig"] = relationship(back_populates="projects")
    style_profile: Mapped["StyleProfile | None"] = relationship(
        back_populates="projects"
    )
    user: Mapped["User"] = relationship(back_populates="projects")


# 风格样本文件表模型
# 存储用户上传的用于风格分析的样本文件元数据
# 支持文本文件、小说章节等作为风格分析的输入源
class StyleSampleFile(TimestampMixin, Base):
    __tablename__ = "style_sample_files"

    # 样本文件ID主键 - UUID字符串，长度36字符
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    # 外键关联到用户表
    # ondelete="CASCADE": 删除用户时自动删除该用户的所有样本文件
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 用户上传时的原始文件名，用于界面展示
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # 文件的MIME类型，如text/plain、application/pdf等
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 文件在服务器或对象存储中的实际存储路径
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    # 文件大小，单位字节
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    # 文件的字符数（文本文件有效），用于分析进度预估
    character_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 文件的SHA256哈希值，用于去重和完整性校验
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    # 反向关联：一个样本文件对应一个风格分析任务
    job: Mapped["StyleAnalysisJob"] = relationship(back_populates="sample_file")
    # 反向关联：一个样本文件属于一个用户
    user: Mapped["User"] = relationship(back_populates="style_sample_files")


# 风格分析任务表模型
# 存储文风分析任务的完整生命周期信息
# 支持异步任务队列处理，包含任务状态、进度、结果和错误信息
class StyleAnalysisJob(TimestampMixin, Base):
    __tablename__ = "style_analysis_jobs"
    # 复合索引优化查询性能
    __table_args__ = (
        # 按状态和创建时间排序的任务列表查询优化
        Index(
            "ix_style_analysis_jobs_status_created_at",
            "status",
            "created_at",
        ),
        # 重试调度优化：按状态、尝试次数和创建时间排序
        Index(
            "ix_style_analysis_jobs_status_attempt_count_created_at",
            "status",
            "attempt_count",
            "created_at",
        ),
        # 死信任务检测：按状态和最后心跳时间查询卡住的任务
        Index(
            "ix_style_analysis_jobs_status_last_heartbeat_at",
            "status",
            "last_heartbeat_at",
        ),
    )

    # 分析任务ID主键 - UUID字符串，长度36字符
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    # 外键关联到用户表
    # ondelete="CASCADE": 删除用户时自动删除该用户的所有分析任务
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 用户为这个文风设定的名称，便于识别
    style_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # 外键关联到LLM提供商配置，指定用哪个配置来执行分析
    provider_id: Mapped[str] = mapped_column(
        ForeignKey("provider_configs.id"), nullable=False
    )
    # 用于分析的具体模型名称
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 外键关联到样本文件表，指定要分析的文件
    # unique=True: 每个样本文件只能有一个分析任务
    # ondelete="CASCADE": 删除样本文件时自动删除关联的分析任务
    sample_file_id: Mapped[str] = mapped_column(
        ForeignKey("style_sample_files.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # 任务状态：pending(等待)/processing(处理中)/completed(完成)/failed(失败)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True
    )
    # 当前处理阶段：extracting(提取)/analyzing(分析)/summarizing(总结)/generating(生成)
    stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 失败时的错误信息详情
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 分析元数据：统计信息、进度百分比等
    analysis_meta_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 完整分析报告原始结果
    analysis_report_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 提炼后的风格摘要数据
    style_summary_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 生成的提示词包，可直接用于写作
    prompt_pack_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 分布式锁持有者标识，用于多worker环境下的任务调度
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 任务被锁定的时间
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 工作节点最后心跳时间，用于检测任务是否卡住
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pause_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 尝试次数，用于失败重试机制
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 任务实际开始处理的时间
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 任务完成（成功或失败）的时间
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 反向关联：一个分析任务使用一个LLM提供商配置
    provider: Mapped["ProviderConfig"] = relationship(
        back_populates="style_analysis_jobs"
    )
    # 反向关联：一个分析任务对应一个样本文件
    # single_parent=True: 支持级联删除
    sample_file: Mapped["StyleSampleFile"] = relationship(
        back_populates="job", single_parent=True
    )
    # 反向关联：一个分析任务可能生成一个风格配置文件
    style_profile: Mapped["StyleProfile | None"] = relationship(
        back_populates="source_job"
    )
    # 反向关联：一个分析任务属于一个用户
    user: Mapped["User"] = relationship(back_populates="style_analysis_jobs")

    @property
    def style_profile_id(self) -> str | None:
        if self.style_profile is not None:
            return self.style_profile.id
        return None


# 风格配置文件表模型
# 存储完成并保存的文风分析结果
# 这是用户可以在项目中直接引用和复用的文风配置
class StyleProfile(TimestampMixin, Base):
    __tablename__ = "style_profiles"

    # 风格配置ID主键 - UUID字符串，长度36字符
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    # 外键关联到用户表
    # ondelete="CASCADE": 删除用户时自动删除该用户的所有风格配置
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 外键关联到分析任务表，标识这个配置来自哪个分析任务
    # unique=True: 每个分析任务最多生成一个风格配置
    source_job_id: Mapped[str] = mapped_column(
        ForeignKey("style_analysis_jobs.id"), nullable=False, unique=True
    )
    # 生成这个配置时使用的LLM提供商配置ID
    provider_id: Mapped[str] = mapped_column(
        ForeignKey("provider_configs.id"), nullable=False, index=True
    )
    # 生成这个配置时使用的具体模型名称
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 来源样本文件的文件名，用于界面展示
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # 用户定义的文风名称
    style_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # 完整的分析报告数据
    analysis_report_payload: Mapped[str] = mapped_column(Text, nullable=False)
    # 提炼后的风格摘要，包含核心特征
    style_summary_payload: Mapped[str] = mapped_column(Text, nullable=False)
    # 可直接用于写作的提示词包，包含系统提示、示例等
    prompt_pack_payload: Mapped[str] = mapped_column(Text, nullable=False)

    # 反向关联：一个风格配置来自一个分析任务
    source_job: Mapped["StyleAnalysisJob"] = relationship(
        back_populates="style_profile"
    )
    # 反向关联：一个风格配置使用一个LLM提供商配置
    provider: Mapped["ProviderConfig"] = relationship(back_populates="style_profiles")
    # 反向关联：一个风格配置可以被多个项目使用
    projects: Mapped[list["Project"]] = relationship(back_populates="style_profile")
    # 反向关联：一个风格配置属于一个用户
    user: Mapped["User"] = relationship(back_populates="style_profiles")
