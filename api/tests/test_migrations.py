from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.core.config import get_settings


def test_alembic_upgrade_succeeds_on_empty_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "migration-test.db"
    monkeypatch.delenv("PERSONA_ENCRYPTION_KEY", raising=False)
    get_settings.cache_clear()
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    try:
        command.upgrade(alembic_config, "head")
    finally:
        get_settings.cache_clear()

    assert database_path.exists()


def test_project_chapter_migration_moves_legacy_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "legacy-content.db"
    monkeypatch.delenv("PERSONA_ENCRYPTION_KEY", raising=False)
    get_settings.cache_clear()
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    try:
        command.upgrade(alembic_config, "b1c2d3e4f5a6")
        import sqlite3

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                INSERT INTO users (id, username, password_hash)
                VALUES ('user-1', 'owner', 'hash')
                """
            )
            connection.execute(
                """
                INSERT INTO provider_configs (
                    id, user_id, label, base_url, api_key_encrypted,
                    api_key_hint_last4, default_model, is_enabled
                )
                VALUES (
                    'provider-1', 'user-1', 'Provider', 'https://example.com',
                    'encrypted', '0000', 'model', 1
                )
                """
            )
            connection.execute(
                """
                INSERT INTO projects (
                    id, user_id, name, description, status, default_provider_id,
                    default_model, outline_detail, runtime_state, runtime_threads,
                    content, length_preset
                )
                VALUES (
                    'project-1', 'user-1', 'Project', '', 'draft', 'provider-1',
                    'model',
                    '## 第一幕\n\n### 第1章：醒在死牢\n\n### 第2章：案卷上的名字',
                    '', '',
                    '# 第1章：醒在死牢\n\n旧第一章正文\n\n# 第2章：案卷上的名字\n\n旧第二章正文',
                    'short'
                )
                """
            )

        command.upgrade(alembic_config, "head")

        with sqlite3.connect(database_path) as connection:
            project_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(projects)").fetchall()
            }
            chapters = connection.execute(
                """
                SELECT volume_index, chapter_index, title, content, word_count
                FROM project_chapters
                ORDER BY volume_index, chapter_index
                """
            ).fetchall()
    finally:
        get_settings.cache_clear()

    assert "content" not in project_columns
    assert chapters == [
        (0, 0, "第1章：醒在死牢", "旧第一章正文", len("旧第一章正文")),
        (0, 1, "第2章：案卷上的名字", "旧第二章正文", len("旧第二章正文")),
    ]


def test_analysis_job_stage_migration_renames_legacy_stage_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "stage-migration.db"
    monkeypatch.delenv("PERSONA_ENCRYPTION_KEY", raising=False)
    get_settings.cache_clear()
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    try:
        command.upgrade(alembic_config, "0013_plot_skeleton_payload")
        import sqlite3

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                INSERT INTO users (id, username, password_hash)
                VALUES ('user-1', 'owner', 'hash')
                """
            )
            connection.execute(
                """
                INSERT INTO provider_configs (
                    id, user_id, label, base_url, api_key_encrypted,
                    api_key_hint_last4, default_model, is_enabled
                )
                VALUES (
                    'provider-1', 'user-1', 'Provider', 'https://example.com',
                    'encrypted', '0000', 'model', 1
                )
                """
            )
            connection.execute(
                """
                INSERT INTO style_sample_files (
                    id, user_id, original_filename, content_type, storage_path,
                    byte_size, character_count, checksum_sha256, created_at, updated_at
                )
                VALUES (
                    'style-sample-1', 'user-1', 'sample.txt', 'text/plain', '/tmp/style.txt',
                    12, 12, 'abc', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                INSERT INTO plot_sample_files (
                    id, user_id, original_filename, content_type, storage_path,
                    byte_size, character_count, checksum_sha256, created_at, updated_at
                )
                VALUES (
                    'plot-sample-1', 'user-1', 'sample.txt', 'text/plain', '/tmp/plot.txt',
                    12, 12, 'def', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                ),
                (
                    'plot-sample-2', 'user-1', 'sample-2.txt', 'text/plain', '/tmp/plot-2.txt',
                    12, 12, 'ghi', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                INSERT INTO style_analysis_jobs (
                    id, user_id, style_name, provider_id, model_name, sample_file_id,
                    status, stage, attempt_count, created_at, updated_at
                )
                VALUES
                    ('style-job-summary', 'user-1', 'Style Summary', 'provider-1', 'model', 'style-sample-1',
                     'running', 'summarizing', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
            connection.execute(
                """
                INSERT INTO plot_analysis_jobs (
                    id, user_id, plot_name, provider_id, model_name, sample_file_id,
                    status, stage, attempt_count, created_at, updated_at
                )
                VALUES
                    ('plot-job-analyze', 'user-1', 'Plot Analyze', 'provider-1', 'model', 'plot-sample-1',
                     'running', 'analyzing_chunks', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                    ('plot-job-summary', 'user-1', 'Plot Summary', 'provider-1', 'model', 'plot-sample-2',
                     'running', 'summarizing', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )

        command.upgrade(alembic_config, "head")

        with sqlite3.connect(database_path) as connection:
            style_stage = connection.execute(
                "SELECT stage FROM style_analysis_jobs WHERE id = 'style-job-summary'"
            ).fetchone()
            plot_stages = connection.execute(
                "SELECT id, stage FROM plot_analysis_jobs ORDER BY id"
            ).fetchall()
    finally:
        get_settings.cache_clear()

    assert style_stage == ("postprocessing",)
    assert plot_stages == [
        ("plot-job-analyze", "analyzing_focus_chunks"),
        ("plot-job-summary", "postprocessing"),
    ]


def test_alembic_revision_ids_fit_version_column_limit() -> None:
    versions_dir = Path(__file__).resolve().parent.parent / "alembic" / "versions"
    for migration_file in versions_dir.glob("*.py"):
        spec = importlib.util.spec_from_file_location(migration_file.stem, migration_file)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        revision = getattr(module, "revision", "")
        assert isinstance(revision, str)
        assert len(revision) <= 32
