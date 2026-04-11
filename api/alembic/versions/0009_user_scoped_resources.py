"""add user scope to resources

Revision ID: 0009_user_scoped_resources
Revises: 0008_sa_job_hot_path_idx
Create Date: 2026-04-11 00:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0009_user_scoped_resources"
down_revision = "0008_sa_job_hot_path_idx"
branch_labels = None
depends_on = None


def _seed_owner_user_id() -> str | None:
    connection = op.get_bind()
    return connection.execute(sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")).scalar()


def upgrade() -> None:
    with op.batch_alter_table("provider_configs") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
    with op.batch_alter_table("style_sample_files") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
    with op.batch_alter_table("style_profiles") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))

    owner_user_id = _seed_owner_user_id()
    if owner_user_id is not None:
        op.execute(
            sa.text("UPDATE provider_configs SET user_id = :user_id WHERE user_id IS NULL").bindparams(
                user_id=owner_user_id
            )
        )
        op.execute(
            sa.text("UPDATE projects SET user_id = :user_id WHERE user_id IS NULL").bindparams(
                user_id=owner_user_id
            )
        )
        op.execute(
            sa.text("UPDATE style_sample_files SET user_id = :user_id WHERE user_id IS NULL").bindparams(
                user_id=owner_user_id
            )
        )
        op.execute(
            sa.text("UPDATE style_analysis_jobs SET user_id = :user_id WHERE user_id IS NULL").bindparams(
                user_id=owner_user_id
            )
        )
        op.execute(
            sa.text("UPDATE style_profiles SET user_id = :user_id WHERE user_id IS NULL").bindparams(
                user_id=owner_user_id
            )
        )

    with op.batch_alter_table("provider_configs") as batch_op:
        batch_op.alter_column("user_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_provider_configs_user_id",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_provider_configs_user_id", ["user_id"])
    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column("user_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_projects_user_id",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_projects_user_id", ["user_id"])
    with op.batch_alter_table("style_sample_files") as batch_op:
        batch_op.alter_column("user_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_style_sample_files_user_id",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_style_sample_files_user_id", ["user_id"])
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.alter_column("user_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_style_analysis_jobs_user_id",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_style_analysis_jobs_user_id", ["user_id"])
    with op.batch_alter_table("style_profiles") as batch_op:
        batch_op.alter_column("user_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_style_profiles_user_id",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_style_profiles_user_id", ["user_id"])


def downgrade() -> None:
    with op.batch_alter_table("style_profiles") as batch_op:
        batch_op.drop_index("ix_style_profiles_user_id")
        batch_op.drop_constraint("fk_style_profiles_user_id", type_="foreignkey")
        batch_op.drop_column("user_id")
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.drop_index("ix_style_analysis_jobs_user_id")
        batch_op.drop_constraint("fk_style_analysis_jobs_user_id", type_="foreignkey")
        batch_op.drop_column("user_id")
    with op.batch_alter_table("style_sample_files") as batch_op:
        batch_op.drop_index("ix_style_sample_files_user_id")
        batch_op.drop_constraint("fk_style_sample_files_user_id", type_="foreignkey")
        batch_op.drop_column("user_id")
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_index("ix_projects_user_id")
        batch_op.drop_constraint("fk_projects_user_id", type_="foreignkey")
        batch_op.drop_column("user_id")
    with op.batch_alter_table("provider_configs") as batch_op:
        batch_op.drop_index("ix_provider_configs_user_id")
        batch_op.drop_constraint("fk_provider_configs_user_id", type_="foreignkey")
        batch_op.drop_column("user_id")
