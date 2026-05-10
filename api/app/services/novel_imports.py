from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.domain_errors import NotFoundError, UnprocessableEntityError
from app.core.text_processing import clean_and_decode_upload
from app.db.models import ProjectChapter
from app.schemas.novel_imports import (
    NovelImportChapterDraft,
    NovelImportCommitResponse,
    NovelImportDraftDocument,
    NovelImportDraftPreview,
    NovelImportDraftUpdateRequest,
    NovelImportProjectMetadata,
)
from app.schemas.projects import ProjectBibleUpdate, ProjectCreate
from app.services.project_chapters import ProjectChapterService
from app.services.projects import ProjectService

logger = logging.getLogger(__name__)

_CHINESE_NUMBER = r"\d+|[一二三四五六七八九十百千万零〇两]+"
_CHAPTER_HEADING_RE = re.compile(
    rf"^\s*(?P<marker>第\s*(?:{_CHINESE_NUMBER})\s*[章节回卷]|Chapter\s*\d+)(?P<tail>[^\n\r]*)$",
    re.IGNORECASE | re.MULTILINE,
)
_WHITESPACE_LINE_RE = re.compile(r"[ \t\f\v]+")
_MAX_CHAPTER_CONTENT_CHARS = 300_000
_DRAFT_TTL = timedelta(hours=24)


class NovelImportService:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        chapter_service: ProjectChapterService | None = None,
        max_upload_bytes: int | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.chapter_service = chapter_service or ProjectChapterService(
            project_service=self.project_service
        )
        self.max_upload_bytes = max_upload_bytes or get_settings().style_analysis_max_upload_bytes

    async def preview_upload(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        project: NovelImportProjectMetadata,
        rights_confirmed: bool,
        upload_file: UploadFile,
    ) -> NovelImportDraftPreview:
        if not rights_confirmed:
            raise UnprocessableEntityError("请先确认你拥有处理该 TXT 内容的权利")
        self._ensure_txt_upload(upload_file)
        await self._validate_metadata(session, project, user_id=user_id)
        text = await self._read_clean_text(upload_file)
        chapters, warnings = self.parse_txt_chapters(text)
        document = NovelImportDraftDocument(
            draft_id=str(uuid.uuid4()),
            user_id=user_id,
            project=project,
            chapters=chapters,
            warnings=warnings,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + _DRAFT_TTL,
        )
        await self._write_draft(document)
        return self._to_preview(document)

    async def update_draft(
        self,
        session: AsyncSession,
        draft_id: str,
        payload: NovelImportDraftUpdateRequest,
        *,
        user_id: str,
    ) -> NovelImportDraftPreview:
        document = await self._read_draft_or_404(draft_id, user_id=user_id)
        await self._validate_metadata(session, payload.project, user_id=user_id)
        chapters = self._normalize_chapters(payload.chapters)
        document.project = payload.project
        document.chapters = chapters
        await self._write_draft(document)
        return self._to_preview(document)

    async def commit_draft(
        self,
        session: AsyncSession,
        draft_id: str,
        *,
        user_id: str,
    ) -> NovelImportCommitResponse:
        document = await self._read_draft_or_404(draft_id, user_id=user_id)
        chapters = self._normalize_chapters(document.chapters)
        project = await self.project_service.create(
            session,
            ProjectCreate(
                name=document.project.project_name,
                description="",
                status="draft",
                default_provider_id=document.project.default_provider_id,
                default_model=document.project.default_model,
                style_profile_id=document.project.style_profile_id,
                plot_profile_id=document.project.plot_profile_id,
                generation_profile=document.project.generation_profile,
                project_origin="txt_import_rewrite",
            ),
            user_id=user_id,
        )
        await self.project_service.update_bible(
            session,
            project.id,
            ProjectBibleUpdate(outline_detail=self._build_outline_detail(chapters)),
            user_id=user_id,
        )
        created = await self.chapter_service.sync_outline(session, project.id, user_id=user_id)
        chapter_map = {
            (chapter.volume_index, chapter.chapter_index): chapter
            for chapter in created
        }
        for index, draft_chapter in enumerate(chapters):
            chapter = chapter_map.get((0, index))
            if chapter is None:
                raise UnprocessableEntityError("导入章节同步失败，请重试")
            self._apply_imported_content(chapter, draft_chapter)
        await self.chapter_service.repository.flush(session)
        await self._delete_draft(draft_id)
        return NovelImportCommitResponse(project_id=project.id)

    @staticmethod
    def parse_txt_chapters(text: str) -> tuple[list[NovelImportChapterDraft], list[str]]:
        normalized = _normalize_txt(text)
        if not normalized.strip():
            raise UnprocessableEntityError("上传的 TXT 文件为空")
        matches = list(_CHAPTER_HEADING_RE.finditer(normalized))
        if not matches:
            return (
                [
                    _build_chapter_draft(
                        client_id="chapter-1",
                        title="第1章",
                        content=normalized.strip(),
                    )
                ],
                ["no_standard_chapter_headings"],
            )

        chapters: list[NovelImportChapterDraft] = []
        prefix = normalized[: matches[0].start()].strip()
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
            content = normalized[start:end].strip()
            title = _chapter_heading_title(match)
            if prefix and index == 0:
                content = f"{prefix}\n\n{content}".strip()
            chapters.append(
                _build_chapter_draft(
                    client_id=f"chapter-{index + 1}",
                    title=title,
                    content=content,
                )
            )
        return chapters, []

    async def _validate_metadata(
        self,
        session: AsyncSession,
        project: NovelImportProjectMetadata,
        *,
        user_id: str,
    ) -> None:
        await self.project_service.provider_service.ensure_enabled(
            session,
            project.default_provider_id,
            user_id=user_id,
        )
        if project.style_profile_id:
            await self.project_service.style_profile_service.get_or_404(
                session,
                project.style_profile_id,
                user_id=user_id,
            )
        if project.plot_profile_id:
            await self.project_service.plot_profile_service.get_or_404(
                session,
                project.plot_profile_id,
                user_id=user_id,
            )

    def _ensure_txt_upload(self, upload_file: UploadFile) -> None:
        filename = (upload_file.filename or "").strip().lower()
        content_type = (upload_file.content_type or "").strip().lower()
        if not filename.endswith(".txt"):
            raise UnprocessableEntityError("仅支持上传 .txt 小说文件")
        if content_type and content_type not in {
            "text/plain",
            "application/octet-stream",
            "text/markdown",
        }:
            raise UnprocessableEntityError("仅支持上传 TXT 文本文件")

    async def _read_clean_text(self, upload_file: UploadFile) -> str:
        chunks: list[str] = []
        try:
            async for chunk in clean_and_decode_upload(upload_file, max_bytes=self.max_upload_bytes):
                chunks.append(chunk.decode("utf-8"))
        except UnprocessableEntityError:
            raise
        except UnicodeError as exc:
            raise UnprocessableEntityError(
                "无法识别 TXT 文件编码，请使用 UTF-8 或 GB18030 保存后重试"
            ) from exc
        except Exception as exc:
            logger.exception(
                "failed to read novel import upload",
                extra={"filename": upload_file.filename},
            )
            raise UnprocessableEntityError("读取 TXT 文件失败，请重新选择文件后重试") from exc
        text = "".join(chunks)
        if not text.strip():
            raise UnprocessableEntityError("上传的 TXT 文件为空")
        return text

    @staticmethod
    def _normalize_chapters(
        chapters: list[NovelImportChapterDraft],
    ) -> list[NovelImportChapterDraft]:
        normalized: list[NovelImportChapterDraft] = []
        for index, chapter in enumerate(chapters):
            title = chapter.title.strip()
            content = chapter.content.strip()
            if not title:
                raise UnprocessableEntityError("章节标题不能为空")
            if len(content) > _MAX_CHAPTER_CONTENT_CHARS:
                raise UnprocessableEntityError("单章内容过长，请拆分后再导入")
            normalized.append(
                NovelImportChapterDraft(
                    client_id=chapter.client_id or f"chapter-{index + 1}",
                    title=title,
                    content=content,
                    word_count=len(content),
                )
            )
        return normalized

    @staticmethod
    def _apply_imported_content(
        chapter: ProjectChapter,
        draft_chapter: NovelImportChapterDraft,
    ) -> None:
        chapter.content = draft_chapter.content
        chapter.word_count = len(draft_chapter.content)
        ProjectChapterService._clear_memory_sync(chapter)

    @staticmethod
    def _build_outline_detail(chapters: list[NovelImportChapterDraft]) -> str:
        lines = ["## 第1卷 导入正文"]
        for index, chapter in enumerate(chapters, start=1):
            clean_title = _strip_chapter_heading_prefix(chapter.title, index)
            heading = f"### 第 {index} 章 {clean_title}".rstrip()
            lines.extend(
                [
                    "",
                    heading,
                    "- 导入章节：正文内容为准；本细纲仅用于章节导航兼容。",
                ]
            )
        return "\n".join(lines).strip()

    async def _read_draft_or_404(
        self,
        draft_id: str,
        *,
        user_id: str,
    ) -> NovelImportDraftDocument:
        path = self._draft_path(draft_id)
        if not path.exists():
            raise NotFoundError("导入草稿不存在或已过期")
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as handle:
                payload = json.loads(await handle.read())
            document = NovelImportDraftDocument.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise NotFoundError("导入草稿不存在或已过期") from exc
        if document.user_id != user_id:
            raise NotFoundError("导入草稿不存在或已过期")
        if document.expires_at < datetime.now(UTC):
            await self._delete_draft(draft_id)
            raise NotFoundError("导入草稿不存在或已过期")
        return document

    async def _write_draft(self, document: NovelImportDraftDocument) -> None:
        path = self._draft_path(document.draft_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "w", encoding="utf-8") as handle:
            await handle.write(document.model_dump_json())

    async def _delete_draft(self, draft_id: str) -> None:
        path = self._draft_path(draft_id)
        if path.exists():
            path.unlink()

    def _draft_path(self, draft_id: str) -> Path:
        try:
            normalized_draft_id = str(uuid.UUID(draft_id))
        except ValueError as exc:
            raise NotFoundError("导入草稿不存在或已过期") from exc
        return (
            Path(get_settings().storage_dir).expanduser()
            / "novel-import-drafts"
            / f"{normalized_draft_id}.json"
        )

    @staticmethod
    def _to_preview(document: NovelImportDraftDocument) -> NovelImportDraftPreview:
        return NovelImportDraftPreview(
            draft_id=document.draft_id,
            project=document.project,
            chapters=document.chapters,
            warnings=document.warnings,
            created_at=document.created_at,
            expires_at=document.expires_at,
        )


def _normalize_txt(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    lines = [_WHITESPACE_LINE_RE.sub(" ", line).strip() for line in text.split("\n")]
    collapsed: list[str] = []
    blank_seen = False
    for line in lines:
        if not line:
            if not blank_seen:
                collapsed.append("")
            blank_seen = True
            continue
        collapsed.append(line)
        blank_seen = False
    return "\n".join(collapsed).strip()


def _chapter_heading_title(match: re.Match[str]) -> str:
    marker = re.sub(r"\s+", "", match.group("marker").strip())
    tail = match.group("tail").strip()
    return f"{marker} {tail}".strip()


def _build_chapter_draft(
    *,
    client_id: str,
    title: str,
    content: str,
) -> NovelImportChapterDraft:
    clean_title = title.strip()
    clean_content = content.strip()
    if len(clean_title) > 200:
        raise UnprocessableEntityError("章节标题过长，请缩短后再导入")
    if len(clean_content) > _MAX_CHAPTER_CONTENT_CHARS:
        raise UnprocessableEntityError("单章内容过长，请拆分后再导入")
    return NovelImportChapterDraft(
        client_id=client_id,
        title=clean_title,
        content=clean_content,
        word_count=len(clean_content),
    )


def _strip_chapter_heading_prefix(title: str, index: int) -> str:
    stripped = re.sub(
        rf"^\s*第\s*(?:{index}|{_CHINESE_NUMBER})\s*[章节回卷]\s*[:：、.．-]?\s*",
        "",
        title,
    ).strip()
    return stripped or title.strip()

