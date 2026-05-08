from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import UnprocessableEntityError
from app.db.models import ProjectPromptAsset
from app.db.repositories.project_prompt_assets import ProjectPromptAssetRepository
from app.schemas.projects import (
    PromptStackAssetManifestItem,
    PromptStackLayerManifestItem,
    PromptStackManifest,
    PromptStackPreviewRequest,
    PromptStackPreviewResponse,
    ProjectPromptAssetCreate,
    ProjectPromptAssetUpdate,
)
from app.services.project_chapters import ProjectChapterService
from app.services.projects import ProjectService

LOREBOOK_ASSET_BUDGET = 8000
CHARACTER_CARD_ASSET_BUDGET = 8000
AUTHOR_NOTE_ASSET_BUDGET = 3000
_TRUNCATED_MARKER = "\n\n（已按上下文预算截断）"

_KIND_LAYER = {
    "lorebook_entry": ("active_lorebook_entries", "Active Lorebook Entries", LOREBOOK_ASSET_BUDGET),
    "character_card": ("active_character_cards", "Active Character Cards", CHARACTER_CARD_ASSET_BUDGET),
    "author_note": ("author_notes", "Author Notes", AUTHOR_NOTE_ASSET_BUDGET),
}


@dataclass(frozen=True)
class SelectedPromptAsset:
    id: str
    kind: str
    scope: str
    chapter_id: str | None
    title: str
    content: str
    priority: int
    match_reasons: list[str]
    matched_keywords: list[str]


@dataclass(frozen=True)
class PromptStackLayer:
    key: str
    title: str
    content: str
    budget: int | None = None
    assets: list[SelectedPromptAsset] = field(default_factory=list)
    original_char_count: int | None = None

    @property
    def char_count(self) -> int:
        return len(self.content)

    @property
    def truncated(self) -> bool:
        return self.original_char_count is not None and self.original_char_count > len(self.content)


@dataclass(frozen=True)
class PromptStackSelection:
    layers: list[PromptStackLayer]
    selected_assets: list[SelectedPromptAsset]
    manifest: PromptStackManifest

    @property
    def prompt_text(self) -> str:
        return "\n\n".join(layer.content for layer in self.layers if layer.content.strip())


class PromptStackService:
    def __init__(
        self,
        repository: ProjectPromptAssetRepository | None = None,
        project_service: ProjectService | None = None,
        chapter_service: ProjectChapterService | None = None,
    ) -> None:
        self.repository = repository or ProjectPromptAssetRepository()
        self.project_service = project_service or ProjectService()
        self.chapter_service = chapter_service or ProjectChapterService(
            project_service=self.project_service
        )

    async def list_assets(
        self,
        session: AsyncSession,
        project_id: str,
        *,
        user_id: str,
    ) -> list[ProjectPromptAsset]:
        await self.project_service.get_or_404(session, project_id, user_id=user_id)
        return await self.repository.list_by_project_id(session, project_id)

    async def get_asset_or_404(
        self,
        session: AsyncSession,
        project_id: str,
        asset_id: str,
        *,
        user_id: str,
    ) -> ProjectPromptAsset:
        await self.project_service.get_or_404(session, project_id, user_id=user_id)
        from app.core.domain_errors import NotFoundError

        asset = await self.repository.get_by_id(session, asset_id, project_id=project_id)
        if asset is None:
            raise NotFoundError("Prompt 资产不存在")
        return asset

    async def create_asset(
        self,
        session: AsyncSession,
        project_id: str,
        payload: ProjectPromptAssetCreate,
        *,
        user_id: str,
    ) -> ProjectPromptAsset:
        await self.project_service.get_or_404(session, project_id, user_id=user_id)
        await self._validate_scope(
            session,
            project_id=project_id,
            scope=payload.scope,
            chapter_id=payload.chapter_id,
            user_id=user_id,
        )
        return await self.repository.create(
            session,
            project_id=project_id,
            kind=payload.kind,
            scope=payload.scope,
            chapter_id=payload.chapter_id if payload.scope == "chapter" else None,
            title=payload.title.strip(),
            content=payload.content,
            keywords=_normalize_keywords(payload.keywords),
            enabled=payload.enabled,
            always_on=payload.always_on,
            priority=payload.priority,
        )

    async def update_asset(
        self,
        session: AsyncSession,
        project_id: str,
        asset_id: str,
        payload: ProjectPromptAssetUpdate,
        *,
        user_id: str,
    ) -> ProjectPromptAsset:
        asset = await self.get_asset_or_404(
            session,
            project_id,
            asset_id,
            user_id=user_id,
        )
        data = payload.model_dump(exclude_unset=True)
        scope = data.get("scope", asset.scope)
        chapter_id = data.get("chapter_id", asset.chapter_id)
        await self._validate_scope(
            session,
            project_id=project_id,
            scope=scope,
            chapter_id=chapter_id,
            user_id=user_id,
        )
        if scope == "project":
            chapter_id = None

        for field_name in ("kind", "scope", "title", "content", "enabled", "always_on", "priority"):
            if field_name not in data:
                continue
            value = data[field_name]
            if field_name == "title":
                value = str(value).strip()
            setattr(asset, field_name, value)
        if "chapter_id" in data or "scope" in data:
            asset.chapter_id = chapter_id
        if "keywords" in data:
            asset.keywords_payload = _normalize_keywords(data["keywords"] or [])
        await self.repository.flush(session)
        return asset

    async def delete_asset(
        self,
        session: AsyncSession,
        project_id: str,
        asset_id: str,
        *,
        user_id: str,
    ) -> None:
        asset = await self.get_asset_or_404(
            session,
            project_id,
            asset_id,
            user_id=user_id,
        )
        await self.repository.delete(session, asset)

    async def preview(
        self,
        session: AsyncSession,
        project_id: str,
        payload: PromptStackPreviewRequest,
        *,
        user_id: str,
        base_layers: list[PromptStackLayer] | None = None,
    ) -> PromptStackPreviewResponse:
        await self.project_service.get_or_404(session, project_id, user_id=user_id)
        if payload.chapter_id:
            await self.chapter_service.get_or_404(
                session,
                project_id,
                payload.chapter_id,
                user_id=user_id,
            )
        assets = await self.repository.list_by_project_id(session, project_id)
        selection = build_prompt_stack_selection(
            assets=assets,
            chapter_id=payload.chapter_id,
            activation_text="\n".join(
                [
                    payload.current_chapter_context,
                    payload.text_before_cursor,
                    payload.user_context,
                ]
            ),
            base_layers=base_layers,
        )
        return PromptStackPreviewResponse(
            prompt=selection.prompt_text,
            manifest=selection.manifest,
        )

    async def select_for_runtime(
        self,
        session: AsyncSession,
        project_id: str,
        *,
        user_id: str,
        chapter_id: str | None,
        current_chapter_context: str,
        text_before_cursor: str,
        user_context: str = "",
    ) -> PromptStackSelection:
        await self.project_service.get_or_404(session, project_id, user_id=user_id)
        assets = await self.repository.list_by_project_id(session, project_id)
        return build_prompt_stack_selection(
            assets=assets,
            chapter_id=chapter_id,
            activation_text="\n".join(
                [current_chapter_context, text_before_cursor, user_context]
            ),
        )

    async def _validate_scope(
        self,
        session: AsyncSession,
        *,
        project_id: str,
        scope: str,
        chapter_id: str | None,
        user_id: str,
    ) -> None:
        if scope == "chapter":
            if not chapter_id:
                raise UnprocessableEntityError("章节级 Prompt 资产必须绑定章节")
            await self.chapter_service.get_or_404(
                session,
                project_id,
                chapter_id,
                user_id=user_id,
            )
            return
        if chapter_id:
            raise UnprocessableEntityError("项目级 Prompt 资产不能绑定章节")


def build_prompt_stack_selection(
    *,
    assets: list[ProjectPromptAsset],
    chapter_id: str | None,
    activation_text: str,
    base_layers: list[PromptStackLayer] | None = None,
) -> PromptStackSelection:
    selected = _select_assets(
        assets=assets,
        chapter_id=chapter_id,
        activation_text=activation_text,
    )
    layers = list(base_layers or [])
    for kind, (key, title, budget) in _KIND_LAYER.items():
        kind_assets = [asset for asset in selected if asset.kind == kind]
        content, original_len = _render_asset_layer(title, kind_assets, budget)
        if content:
            layers.append(
                PromptStackLayer(
                    key=key,
                    title=title,
                    content=content,
                    budget=budget,
                    assets=kind_assets,
                    original_char_count=original_len,
                )
            )
    final_prompt = "\n\n".join(layer.content for layer in layers if layer.content.strip())
    manifest = _build_manifest(layers, selected, final_prompt_char_count=len(final_prompt))
    return PromptStackSelection(
        layers=layers,
        selected_assets=selected,
        manifest=manifest,
    )


def _select_assets(
    *,
    assets: list[ProjectPromptAsset],
    chapter_id: str | None,
    activation_text: str,
) -> list[SelectedPromptAsset]:
    haystack = activation_text.casefold()
    selected: list[SelectedPromptAsset] = []
    for asset in assets:
        if not asset.enabled:
            continue
        if asset.scope == "chapter" and asset.chapter_id != chapter_id:
            continue
        reasons: list[str] = []
        matched_keywords: list[str] = []
        if asset.always_on:
            reasons.append("always_on")
        for keyword in asset.keywords:
            if keyword.casefold() and keyword.casefold() in haystack:
                matched_keywords.append(keyword)
        if matched_keywords:
            reasons.append("keyword")
        if not reasons:
            continue
        selected.append(
            SelectedPromptAsset(
                id=asset.id,
                kind=asset.kind,
                scope=asset.scope,
                chapter_id=asset.chapter_id,
                title=asset.title,
                content=asset.content,
                priority=asset.priority,
                match_reasons=reasons,
                matched_keywords=matched_keywords,
            )
        )
    return sorted(selected, key=lambda item: (-item.priority, item.title, item.id))


def _render_asset_layer(
    title: str,
    assets: list[SelectedPromptAsset],
    budget: int,
) -> tuple[str, int]:
    if not assets:
        return "", 0
    body = "\n\n".join(
        f"## {asset.title}\n\n{asset.content.strip()}" for asset in assets if asset.content.strip()
    ).strip()
    if not body:
        return "", 0
    content = f"# {title}\n\n{body}"
    return _limit_text(content, budget), len(content)


def _build_manifest(
    layers: list[PromptStackLayer],
    selected_assets: list[SelectedPromptAsset],
    *,
    final_prompt_char_count: int,
) -> PromptStackManifest:
    asset_items = [
        _asset_manifest_item(
            asset,
            truncated=any(layer.truncated for layer in layers if asset in layer.assets),
        )
        for asset in selected_assets
    ]
    asset_item_by_id = {item.id: item for item in asset_items}
    return PromptStackManifest(
        layers=[
            PromptStackLayerManifestItem(
                key=layer.key,
                title=layer.title,
                char_count=layer.char_count,
                budget=layer.budget,
                truncated=layer.truncated,
                assets=[asset_item_by_id[asset.id] for asset in layer.assets],
            )
            for layer in layers
        ],
        selected_assets=asset_items,
        total_selected_assets=len(selected_assets),
        final_prompt_char_count=final_prompt_char_count,
    )


def _asset_manifest_item(
    asset: SelectedPromptAsset,
    *,
    truncated: bool,
) -> PromptStackAssetManifestItem:
    return PromptStackAssetManifestItem(
        id=asset.id,
        kind=asset.kind,
        scope=asset.scope,
        chapter_id=asset.chapter_id,
        title=asset.title,
        priority=asset.priority,
        char_count=len(asset.content),
        original_char_count=len(asset.content),
        truncated=truncated,
        match_reasons=asset.match_reasons,
        matched_keywords=asset.matched_keywords,
    )


def _normalize_keywords(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        keyword = str(value).strip()
        if keyword and keyword not in normalized:
            normalized.append(keyword)
    return normalized


def _limit_text(text: str, max_chars: int) -> str:
    stripped = (text or "").strip()
    if len(stripped) <= max_chars:
        return stripped
    body_budget = max(max_chars - len(_TRUNCATED_MARKER), 0)
    return stripped[:body_budget].rstrip() + _TRUNCATED_MARKER
