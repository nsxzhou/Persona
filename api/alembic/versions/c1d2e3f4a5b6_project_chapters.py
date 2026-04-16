"""project chapters

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-04-16 13:30:00.000000

"""
from __future__ import annotations

import re
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _parse_outline_chapters(outline_detail: str) -> list[tuple[int, int, str]]:
    chapters: list[tuple[int, int, str]] = []
    volume_blocks = [b for b in re.split(r"^(?=## )", outline_detail, flags=re.MULTILINE) if b.strip()]
    for volume_index, block in enumerate(volume_blocks):
        if not re.search(r"^## (.+)$", block, flags=re.MULTILINE):
            continue
        chapter_index = 0
        for match in re.finditer(r"^### (.+)$", block, flags=re.MULTILINE):
            chapters.append((volume_index, chapter_index, match.group(1).strip()))
            chapter_index += 1
    return chapters


def _split_legacy_content(content: str) -> dict[str, str]:
    matches = list(re.finditer(r"^# (.+)$", content, flags=re.MULTILINE))
    if not matches:
        return {}

    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        result[match.group(1).strip()] = content[start:end].strip()
    return result


def upgrade() -> None:
    op.create_table(
        "project_chapters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("volume_index", sa.Integer(), nullable=False),
        sa.Column("chapter_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "volume_index",
            "chapter_index",
            name="uq_project_chapter_position",
        ),
    )
    op.create_index(
        op.f("ix_project_chapters_project_id"),
        "project_chapters",
        ["project_id"],
        unique=False,
    )

    connection = op.get_bind()
    projects = connection.execute(
        sa.text("SELECT id, outline_detail, content FROM projects")
    ).mappings().all()
    for project in projects:
        project_id = project["id"]
        outline_chapters = _parse_outline_chapters(project["outline_detail"] or "")
        legacy_content = project["content"] or ""
        content_by_title = _split_legacy_content(legacy_content)
        used_legacy = False

        for volume_index, chapter_index, title in outline_chapters:
            chapter_content = content_by_title.get(title, "")
            if chapter_content:
                used_legacy = True
            connection.execute(
                sa.text(
                    """
                    INSERT INTO project_chapters (
                        id, project_id, volume_index, chapter_index,
                        title, content, word_count
                    )
                    VALUES (
                        :id, :project_id, :volume_index, :chapter_index,
                        :title, :content, :word_count
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "volume_index": volume_index,
                    "chapter_index": chapter_index,
                    "title": title,
                    "content": chapter_content,
                    "word_count": len(chapter_content),
                },
            )

        if legacy_content.strip() and not used_legacy:
            if outline_chapters:
                volume_index, chapter_index, title = outline_chapters[0]
                connection.execute(
                    sa.text(
                        """
                        UPDATE project_chapters
                        SET content = :content, word_count = :word_count
                        WHERE project_id = :project_id
                          AND volume_index = :volume_index
                          AND chapter_index = :chapter_index
                        """
                    ),
                    {
                        "content": legacy_content.strip(),
                        "word_count": len(legacy_content.strip()),
                        "project_id": project_id,
                        "volume_index": volume_index,
                        "chapter_index": chapter_index,
                    },
                )
            else:
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO project_chapters (
                            id, project_id, volume_index, chapter_index,
                            title, content, word_count
                        )
                        VALUES (
                            :id, :project_id, 0, 0,
                            :title, :content, :word_count
                        )
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "project_id": project_id,
                        "title": "旧正文",
                        "content": legacy_content.strip(),
                        "word_count": len(legacy_content.strip()),
                    },
                )

    op.drop_column("projects", "content")


def downgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
    )
    connection = op.get_bind()
    projects = connection.execute(sa.text("SELECT id FROM projects")).mappings().all()
    for project in projects:
        chapters = connection.execute(
            sa.text(
                """
                SELECT title, content
                FROM project_chapters
                WHERE project_id = :project_id
                ORDER BY volume_index, chapter_index
                """
            ),
            {"project_id": project["id"]},
        ).mappings().all()
        content = "\n\n".join(
            f"# {chapter['title']}\n\n{chapter['content']}".strip()
            for chapter in chapters
            if chapter["content"]
        )
        connection.execute(
            sa.text("UPDATE projects SET content = :content WHERE id = :project_id"),
            {"content": content, "project_id": project["id"]},
        )
    op.drop_index(op.f("ix_project_chapters_project_id"), table_name="project_chapters")
    op.drop_table("project_chapters")
