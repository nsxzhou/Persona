"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-07 22:45:00.000000
"""

from __future__ import annotations

# Alembic 操作对象：提供 create_table / add_column / create_index 等迁移指令
from alembic import op
# SQLAlchemy 的类型与列定义工具：用于描述表结构（列类型、约束、默认值等）
import sqlalchemy as sa


# 本次迁移的唯一 ID：用于在 alembic_version 表里记录当前数据库版本
revision = "0001_initial"
# 上一个迁移的 revision（None 表示这是第一个迁移）
down_revision = None
# 分支标签：用于多分支迁移场景（本项目不使用）
branch_labels = None
# 依赖迁移：用于跨分支依赖关系（本项目不使用）
depends_on = None


# upgrade: 把数据库“升级到这个版本”时要执行的变更
def upgrade() -> None:
    # 用户表：存储登录账号（用户名/密码哈希）及审计时间
    op.create_table(
        "users",
        # 业务上用字符串 UUID（36 长度）作为主键，避免自增 ID 带来的可猜测性
        sa.Column("id", sa.String(length=36), nullable=False),
        # username 唯一，作为登录凭证之一
        sa.Column("username", sa.String(length=64), nullable=False),
        # password_hash 存储的是哈希后的密码（不要存明文）
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        # created_at/updated_at 使用数据库的 now() 作为默认值，保证无论从哪里写入都能自动生成时间
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    # 模型提供商配置表：保存不同 LLM Provider 的连接信息与默认模型
    op.create_table(
        "provider_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        # label：给配置起个可读名字（例如 “公司 OpenAI”、“本地代理”）
        sa.Column("label", sa.String(length=100), nullable=False),
        # base_url：API 网关/代理地址
        sa.Column("base_url", sa.String(length=255), nullable=False),
        # api_key_encrypted：加密后的 API Key（落库时只存密文）
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        # api_key_hint_last4：只存后四位用于 UI 展示/排错（避免泄露完整密钥）
        sa.Column("api_key_hint_last4", sa.String(length=4), nullable=False),
        # default_model：该 Provider 默认使用的模型名
        sa.Column("default_model", sa.String(length=100), nullable=False),
        # is_enabled：是否启用该配置（便于灰度/停用）
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        # 最近一次连通性测试结果：用于在后台快速判断配置是否可用
        sa.Column("last_test_status", sa.String(length=32), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # 会话表：管理登录会话 token（只存 hash），以及过期/访问时间
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        # user_id 外键关联 users.id，用户被删除时会级联删除其会话
        sa.Column("user_id", sa.String(length=36), nullable=False),
        # token_hash：token 的哈希值（安全起见，不存明文 token）
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        # expires_at：会话过期时间
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        # last_accessed_at：用于滑动过期/安全审计
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # 唯一约束：同一个 token_hash 不允许重复插入
        sa.UniqueConstraint("token_hash"),
    )
    # 索引：加速按 token_hash 查询会话（例如鉴权中间件/依赖）
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"], unique=False)

    # 项目表：一个 Persona/Novel 项目的业务容器，关联默认 provider 与模型
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        # 项目名称：用于列表展示
        sa.Column("name", sa.String(length=120), nullable=False),
        # 项目描述：较长文本
        sa.Column("description", sa.Text(), nullable=False),
        # status：项目状态（例如 active/archived 等，具体枚举由业务层约束）
        sa.Column("status", sa.String(length=16), nullable=False),
        # 默认 Provider：引用 provider_configs.id
        sa.Column("default_provider_id", sa.String(length=36), nullable=False),
        # 默认模型：可能与 provider 的 default_model 不同（项目级覆盖）
        sa.Column("default_model", sa.String(length=100), nullable=False),
        # style_profile_id：可选的风格配置（当前允许为空，后续可扩展成外键）
        sa.Column("style_profile_id", sa.String(length=36), nullable=True),
        # archived_at：软归档时间（不一定删除数据）
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["default_provider_id"], ["provider_configs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


# downgrade: 把数据库“回滚到上一个版本”时要撤销的变更
def downgrade() -> None:
    # 回滚顺序通常和创建顺序相反，避免外键依赖导致 drop 失败
    op.drop_table("projects")
    op.drop_index("ix_sessions_token_hash", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("provider_configs")
    op.drop_table("users")
