from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # Argon2 哈希值（非明文）
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

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


class Session(TimestampMixin, Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # HMAC 哈希（非原始令牌）
    token_hash: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="sessions")


class ProviderConfig(TimestampMixin, Base):
    __tablename__ = "provider_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    # AES-GCM 密文
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_hint_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    default_model: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_test_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_test_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    projects: Mapped[list["Project"]] = relationship(back_populates="provider")
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


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # draft / active / paused
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    default_provider_id: Mapped[str] = mapped_column(
        ForeignKey("provider_configs.id"), nullable=False, index=True
    )
    default_model: Mapped[str] = mapped_column(String(100), nullable=False)
    style_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("style_profiles.id"), nullable=True, index=True
    )
    # 蓝图层：作者手动编辑的创作规划资产
    inspiration: Mapped[str] = mapped_column(Text, nullable=False, default="")
    world_building: Mapped[str] = mapped_column(Text, nullable=False, default="")
    characters: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outline_master: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outline_detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 活态层：AI 写作后自动提议的运行时状态
    runtime_state: Mapped[str] = mapped_column(Text, nullable=False, default="")
    runtime_threads: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # short / medium / long
    length_preset: Mapped[str] = mapped_column(String(16), nullable=False, default="short")
    # 逐拍写作完成时是否静默自动同步记忆
    auto_sync_memory: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    provider: Mapped["ProviderConfig"] = relationship(back_populates="projects")
    style_profile: Mapped["StyleProfile | None"] = relationship(
        back_populates="projects"
    )
    user: Mapped["User"] = relationship(back_populates="projects")
    chapters: Mapped[list["ProjectChapter"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectChapter(TimestampMixin, Base):
    __tablename__ = "project_chapters"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "volume_index",
            "chapter_index",
            name="uq_project_chapter_position",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    volume_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chapter_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    memory_sync_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    memory_sync_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    memory_sync_scope: Mapped[str | None] = mapped_column(String(32), nullable=True)
    memory_sync_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    memory_sync_checked_content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    memory_sync_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    memory_sync_proposed_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    memory_sync_proposed_threads: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="chapters")


class StyleSampleFile(TimestampMixin, Base):
    __tablename__ = "style_sample_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    character_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    job: Mapped["StyleAnalysisJob"] = relationship(back_populates="sample_file")
    user: Mapped["User"] = relationship(back_populates="style_sample_files")


class StyleAnalysisJob(TimestampMixin, Base):
    __tablename__ = "style_analysis_jobs"
    __table_args__ = (
        Index(
            "ix_style_analysis_jobs_status_created_at",
            "status",
            "created_at",
        ),
        Index(
            "ix_style_analysis_jobs_status_attempt_count_created_at",
            "status",
            "attempt_count",
            "created_at",
        ),
        Index(
            "ix_style_analysis_jobs_status_last_heartbeat_at",
            "status",
            "last_heartbeat_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
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
    # pending / processing / completed / failed / paused
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True
    )
    # extracting / analyzing / summarizing / generating
    stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_meta_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analysis_report_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    style_summary_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_pack_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 多 worker 并发场景下的抢占锁持有者标识
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pause_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    provider: Mapped["ProviderConfig"] = relationship(
        back_populates="style_analysis_jobs"
    )
    sample_file: Mapped["StyleSampleFile"] = relationship(
        back_populates="job", single_parent=True
    )
    style_profile: Mapped["StyleProfile | None"] = relationship(
        back_populates="source_job"
    )
    user: Mapped["User"] = relationship(back_populates="style_analysis_jobs")

    @property
    def style_profile_id(self) -> str | None:
        if self.style_profile is not None:
            return self.style_profile.id
        return None


class StyleProfile(TimestampMixin, Base):
    __tablename__ = "style_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_job_id: Mapped[str] = mapped_column(
        ForeignKey("style_analysis_jobs.id"), nullable=False, unique=True
    )
    provider_id: Mapped[str] = mapped_column(
        ForeignKey("provider_configs.id"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    style_name: Mapped[str] = mapped_column(String(120), nullable=False)
    analysis_report_payload: Mapped[str] = mapped_column(Text, nullable=False)
    style_summary_payload: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_pack_payload: Mapped[str] = mapped_column(Text, nullable=False)

    source_job: Mapped["StyleAnalysisJob"] = relationship(
        back_populates="style_profile"
    )
    provider: Mapped["ProviderConfig"] = relationship(back_populates="style_profiles")
    projects: Mapped[list["Project"]] = relationship(back_populates="style_profile")
    user: Mapped["User"] = relationship(back_populates="style_profiles")
