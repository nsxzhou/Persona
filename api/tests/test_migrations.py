from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def test_alembic_upgrade_succeeds_on_empty_database(tmp_path: Path) -> None:
    database_path = tmp_path / "migration-test.db"
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    command.upgrade(alembic_config, "head")

    assert database_path.exists()

