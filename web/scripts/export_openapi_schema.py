from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: export_openapi_schema.py <output-path>")

    repo_root = Path(__file__).resolve().parents[2]
    api_root = repo_root / "api"
    output_path = Path(sys.argv[1]).resolve()

    os.environ.setdefault("PERSONA_DATABASE_URL", "sqlite+aiosqlite:///./.persona-openapi.db")
    os.environ.setdefault("PERSONA_ENCRYPTION_KEY", "persona-openapi-contract-key-1234567890")
    os.environ.setdefault("PERSONA_STYLE_ANALYSIS_WORKER_ENABLED", "false")

    sys.path.insert(0, str(api_root))

    from app.main import create_app

    schema = create_app().openapi()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
