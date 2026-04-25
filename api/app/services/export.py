from __future__ import annotations

import html
import io
import urllib.parse
from fastapi.responses import StreamingResponse

import ebooklib
from ebooklib import epub

from app.db.models import Project, ProjectChapter


class ExportService:
    @staticmethod
    async def generate_txt_export(project: Project, chapters: list[ProjectChapter]):
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
            def iterfile():
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
