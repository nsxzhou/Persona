from __future__ import annotations

import html
import io
import urllib.parse
from fastapi.responses import StreamingResponse

from ebooklib import epub

from collections.abc import AsyncGenerator

from app.db.models import Project, ProjectChapter
from app.services.project_chapters import ProjectChapterService
from app.services.projects import ProjectService


class ExportService:
    @staticmethod
    async def generate_txt_export(project: Project, chapters: list[ProjectChapter]) -> AsyncGenerator[bytes, None]:
        yield f"{project.name}\n".encode("utf-8")
        yield ("=" * 40 + "\n\n").encode("utf-8")

        current_volume = -1
        for chapter in chapters:
            if chapter.volume_index != current_volume:
                current_volume = chapter.volume_index
                yield f"## 第 {current_volume + 1} 卷\n\n".encode("utf-8")
            yield f"### 第 {chapter.chapter_index + 1} 章 {chapter.title}\n\n".encode("utf-8")
            if chapter.content:
                yield f"{chapter.content}\n\n".encode("utf-8")

    @staticmethod
    def generate_epub_export(project: Project, chapters: list[ProjectChapter]) -> bytes:
        book = epub.EpubBook()
        book.set_title(project.name)
        book.set_language("zh")

        epub_chapters = []
        toc = []
        current_volume = -1
        current_volume_chapters = []

        for chapter in chapters:
            if chapter.volume_index != current_volume:
                if current_volume != -1:
                    toc.append(
                        (epub.Section(f"第 {current_volume + 1} 卷"), current_volume_chapters)
                    )
                current_volume = chapter.volume_index
                current_volume_chapters = []

            file_name = f"chap_{chapter.volume_index}_{chapter.chapter_index}.xhtml"
            c = epub.EpubHtml(
                title=f"第 {chapter.chapter_index + 1} 章 {chapter.title}",
                file_name=file_name,
                lang="zh",
            )
            # 格式化正文为 HTML 段落
            content_html = "".join(
                [f"<p>{html.escape(p, quote=True)}</p>" for p in chapter.content.split("\n") if p.strip()]
            )
            c.content = (
                f"<h2>第 {chapter.chapter_index + 1} 章 {html.escape(chapter.title, quote=True)}</h2>"
                f"{content_html}"
            )
            book.add_item(c)
            epub_chapters.append(c)
            current_volume_chapters.append(c)

        if current_volume != -1:
            toc.append(
                (epub.Section(f"第 {current_volume + 1} 卷"), current_volume_chapters)
            )

        book.toc = toc
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        book.spine = ["nav"] + epub_chapters

        out_io = io.BytesIO()
        epub.write_epub(out_io, book)
        return out_io.getvalue()

    @staticmethod
    def build_export_response(
        project: Project, chapters: list[ProjectChapter], fmt: str
    ) -> StreamingResponse:
        filename = urllib.parse.quote(f"{project.name}.{fmt}")
        if fmt == "epub":
            content = ExportService.generate_epub_export(project, chapters)
            media_type = "application/epub+zip"
            async def iterfile() -> AsyncGenerator[bytes, None]:
                yield content
            return StreamingResponse(
                iterfile(),
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
            )
        else:
            media_type = "text/plain; charset=utf-8"
            return StreamingResponse(
                ExportService.generate_txt_export(project, chapters),
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
            )


class ProjectExportService:
    def __init__(
        self,
        project_service: ProjectService | None = None,
        project_chapter_service: ProjectChapterService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.project_chapter_service = project_chapter_service or ProjectChapterService()

    async def build_project_export_response(
        self,
        session,
        project_id: str,
        *,
        user_id: str,
        fmt: str,
    ) -> StreamingResponse:
        project = await self.project_service.get_or_404(
            session,
            project_id,
            user_id=user_id,
        )
        chapters = await self.project_chapter_service.list(
            session,
            project_id,
            user_id=user_id,
        )
        return ExportService.build_export_response(project, chapters, fmt)
