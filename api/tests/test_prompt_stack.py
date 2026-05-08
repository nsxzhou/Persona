from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_prompt_assets_crud_and_preview_activation(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    project = await _create_project(initialized_client, str(initialized_provider["id"]))
    project_id = project["id"]

    disabled = await initialized_client.post(
        f"/api/v1/projects/{project_id}/prompt-assets",
        json={
            "kind": "lorebook_entry",
            "scope": "project",
            "title": "Disabled lore",
            "content": "SHOULD_NOT_APPEAR",
            "keywords": ["river"],
            "enabled": False,
            "always_on": True,
            "priority": 100,
        },
    )
    assert disabled.status_code == 201

    always_on = await initialized_client.post(
        f"/api/v1/projects/{project_id}/prompt-assets",
        json={
            "kind": "author_note",
            "scope": "project",
            "title": "Near output",
            "content": "Keep tension close to output.",
            "keywords": [],
            "enabled": True,
            "always_on": True,
            "priority": 1,
        },
    )
    assert always_on.status_code == 201

    keyword = await initialized_client.post(
        f"/api/v1/projects/{project_id}/prompt-assets",
        json={
            "kind": "lorebook_entry",
            "scope": "project",
            "title": "River city",
            "content": "The river city has a hidden gate.",
            "keywords": ["river"],
            "enabled": True,
            "always_on": False,
            "priority": 5,
        },
    )
    assert keyword.status_code == 201

    preview = await initialized_client.post(
        f"/api/v1/projects/{project_id}/prompt-stack/preview",
        json={"text_before_cursor": "They crossed the river at dawn."},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert "The river city has a hidden gate." in body["prompt"]
    assert "Keep tension close to output." in body["prompt"]
    assert "SHOULD_NOT_APPEAR" not in body["prompt"]
    assert body["manifest"]["total_selected_assets"] == 2
    assert body["manifest"]["selected_assets"][0]["title"] == "River city"
    assert body["manifest"]["selected_assets"][0]["match_reasons"] == ["keyword"]
    assert body["manifest"]["selected_assets"][1]["match_reasons"] == ["always_on"]

    patch = await initialized_client.patch(
        f"/api/v1/projects/{project_id}/prompt-assets/{keyword.json()['id']}",
        json={"priority": 10, "keywords": ["gate"]},
    )
    assert patch.status_code == 200
    assert patch.json()["keywords"] == ["gate"]

    listed = await initialized_client.get(f"/api/v1/projects/{project_id}/prompt-assets")
    assert listed.status_code == 200
    assert len(listed.json()) == 3

    delete = await initialized_client.delete(
        f"/api/v1/projects/{project_id}/prompt-assets/{always_on.json()['id']}"
    )
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_chapter_scoped_prompt_asset_requires_matching_chapter(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    project = await _create_project(initialized_client, str(initialized_provider["id"]))
    project_id = project["id"]
    sync = await initialized_client.post(f"/api/v1/projects/{project_id}/chapters/sync-outline")
    assert sync.status_code == 200
    chapter_id = sync.json()[0]["id"]

    missing_chapter = await initialized_client.post(
        f"/api/v1/projects/{project_id}/prompt-assets",
        json={
            "kind": "character_card",
            "scope": "chapter",
            "chapter_id": None,
            "title": "Chapter only",
            "content": "Scoped card",
        },
    )
    assert missing_chapter.status_code == 422

    created = await initialized_client.post(
        f"/api/v1/projects/{project_id}/prompt-assets",
        json={
            "kind": "character_card",
            "scope": "chapter",
            "chapter_id": chapter_id,
            "title": "Chapter only",
            "content": "Scoped card",
            "always_on": True,
        },
    )
    assert created.status_code == 201

    without_chapter = await initialized_client.post(
        f"/api/v1/projects/{project_id}/prompt-stack/preview",
        json={},
    )
    assert "Scoped card" not in without_chapter.json()["prompt"]

    with_chapter = await initialized_client.post(
        f"/api/v1/projects/{project_id}/prompt-stack/preview",
        json={"chapter_id": chapter_id},
    )
    assert "Scoped card" in with_chapter.json()["prompt"]


@pytest.mark.asyncio
async def test_runtime_prompt_stack_selection_service(
    app_with_db: FastAPI,
) -> None:
    from app.core.security import hash_password
    from app.db.repositories.auth import AuthRepository
    from app.schemas.projects import ProjectCreate, ProjectPromptAssetCreate
    from app.schemas.provider_configs import ProviderConfigCreate
    from app.services.prompt_stack import PromptStackService
    from app.services.projects import ProjectService
    from app.services.provider_configs import ProviderConfigService

    async with app_with_db.state.session_factory() as session:
        user = await AuthRepository().create_user(
            session,
            username="prompt-stack-owner",
            password_hash=hash_password("password123"),
        )
        provider = await ProviderConfigService().create(
            session,
            ProviderConfigCreate(
                label="Primary",
                base_url="https://api.example.test/v1",
                api_key="sk-test-1234",
                default_model="gpt-4.1-mini",
            ),
            user_id=user.id,
        )
        project = await ProjectService().create(
            session,
            ProjectCreate(
                name="Runtime Stack",
                default_provider_id=provider.id,
                default_model="",
            ),
            user_id=user.id,
        )
        service = PromptStackService()
        await service.create_asset(
            session,
            project.id,
            ProjectPromptAssetCreate(
                kind="lorebook_entry",
                title="Moon gate",
                content="Moon gate lore",
                keywords=["moon"],
                priority=3,
            ),
            user_id=user.id,
        )
        await service.create_asset(
            session,
            project.id,
            ProjectPromptAssetCreate(
                kind="character_card",
                title="Always character",
                content="Character card",
                always_on=True,
                priority=1,
            ),
            user_id=user.id,
        )

        selection = await service.select_for_runtime(
            session,
            project.id,
            user_id=user.id,
            chapter_id=None,
            current_chapter_context="moon rises",
            text_before_cursor="",
        )

    assert "Moon gate lore" in selection.prompt_text
    assert "Character card" in selection.prompt_text
    assert selection.manifest.total_selected_assets == 2
    assert [layer.key for layer in selection.layers] == [
        "active_lorebook_entries",
        "active_character_cards",
    ]


async def _create_project(client: AsyncClient, provider_id: str) -> dict:
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Prompt Stack Project",
            "description": "A project",
            "status": "draft",
            "default_provider_id": provider_id,
            "default_model": "",
            "outline_detail": "",
        },
    )
    assert response.status_code == 201
    project = response.json()
    bible_response = await client.patch(
        f"/api/v1/projects/{project['id']}/bible",
        json={"outline_detail": "## 第1卷\n### 第1章 测试章\n- 目标：进入场景"},
    )
    assert bible_response.status_code == 200
    return project
