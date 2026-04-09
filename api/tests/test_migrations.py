from __future__ import annotations

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
