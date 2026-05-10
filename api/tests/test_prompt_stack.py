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
async def test_apply_prompt_asset_suggestions_creates_updates_and_disables(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    project = await _create_project(initialized_client, str(initialized_provider["id"]))
    project_id = project["id"]

    existing = await initialized_client.post(
        f"/api/v1/projects/{project_id}/prompt-assets",
        json={
            "kind": "lorebook_entry",
            "scope": "project",
            "title": "Old lore",
            "content": "Old content",
            "keywords": ["old"],
            "enabled": True,
            "priority": 1,
        },
    )
    assert existing.status_code == 201
    old_id = existing.json()["id"]

    stale = await initialized_client.post(
        f"/api/v1/projects/{project_id}/prompt-assets",
        json={
            "kind": "author_note",
            "scope": "project",
            "title": "Stale note",
            "content": "Outdated instruction",
            "enabled": True,
            "always_on": True,
        },
    )
    assert stale.status_code == 201
    stale_id = stale.json()["id"]

    apply_response = await initialized_client.post(
        f"/api/v1/projects/{project_id}/prompt-assets/apply-suggestions",
        json={
            "changes": [
                {
                    "action": "new",
                    "rationale": "补齐角色卡",
                    "payload": {
                        "kind": "character_card",
                        "scope": "project",
                        "chapter_id": None,
                        "title": "沈砚",
                        "content": "## 沈砚\n- 查案者",
                        "keywords": ["沈砚"],
                        "enabled": True,
                        "always_on": False,
                        "priority": 20,
                    },
                },
                {
                    "action": "update",
                    "asset_id": old_id,
                    "rationale": "旧世界书需要补充",
                    "payload": {
                        "kind": "lorebook_entry",
                        "scope": "project",
                        "chapter_id": None,
                        "title": "Rain city",
                        "content": "Updated content",
                        "keywords": ["rain"],
                        "enabled": True,
                        "always_on": False,
                        "priority": 8,
                    },
                },
                {
                    "action": "disable",
                    "asset_id": stale_id,
                    "rationale": "重复",
                },
            ]
        },
    )
    assert apply_response.status_code == 200
    changed = apply_response.json()["assets"]
    assert len(changed) == 3

    listed = await initialized_client.get(f"/api/v1/projects/{project_id}/prompt-assets")
    assert listed.status_code == 200
    assets = {asset["id"]: asset for asset in listed.json()}
    assert any(asset["title"] == "沈砚" for asset in assets.values())
    assert assets[old_id]["title"] == "Rain city"
    assert assets[old_id]["keywords"] == ["rain"]
    assert assets[stale_id]["enabled"] is False


@pytest.mark.asyncio
async def test_apply_prompt_asset_suggestions_rejects_cross_project_asset_ids(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    project_a = await _create_project(initialized_client, str(initialized_provider["id"]))
    project_b = await _create_project(initialized_client, str(initialized_provider["id"]))

    other_asset = await initialized_client.post(
        f"/api/v1/projects/{project_b['id']}/prompt-assets",
        json={
            "kind": "lorebook_entry",
            "scope": "project",
            "title": "Other project asset",
            "content": "Other content",
        },
    )
    assert other_asset.status_code == 201

    response = await initialized_client.post(
        f"/api/v1/projects/{project_a['id']}/prompt-assets/apply-suggestions",
        json={
            "changes": [
                {
                    "action": "disable",
                    "asset_id": other_asset.json()["id"],
                    "rationale": "should not cross projects",
                }
            ]
        },
    )

    assert response.status_code == 404


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


@pytest.mark.asyncio
async def test_chapter_expand_runtime_prompt_stack_uses_full_beat_list(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
    app_with_db: FastAPI,
) -> None:
    from app.services.novel_workflow_worker import NovelWorkflowJobExecutor

    project = await _create_project(initialized_client, str(initialized_provider["id"]))
    asset = await initialized_client.post(
        f"/api/v1/projects/{project['id']}/prompt-assets",
        json={
            "kind": "lorebook_entry",
            "scope": "project",
            "title": "Seal lore",
            "content": "The blood seal can only be opened once.",
            "keywords": ["血印"],
            "enabled": True,
            "always_on": False,
            "priority": 5,
        },
    )
    assert asset.status_code == 201

    run_response = await initialized_client.post(
        "/api/v1/novel-workflows",
        json={
            "intent_type": "chapter_expand",
            "project_id": project["id"],
            "beats": ["主角发现血印", "反派抢先开启密室"],
        },
    )
    assert run_response.status_code == 201

    executor = NovelWorkflowJobExecutor()
    context = await executor._load_run_context(
        app_with_db.state.session_factory,
        run_response.json()["id"],
    )

    prompt_stack = context.initial_state["prompt_stack"]
    assert prompt_stack is not None
    assert "The blood seal can only be opened once." in prompt_stack.prompt_text
    assert prompt_stack.manifest.selected_assets[0].matched_keywords == ["血印"]


@pytest.mark.asyncio
async def test_chapter_expand_runtime_context_uses_request_style_profile_override(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
    app_with_db: FastAPI,
) -> None:
    from app.services.novel_workflow_worker import NovelWorkflowJobExecutor

    project = await _create_project(initialized_client, str(initialized_provider["id"]))
    default_profile = await _create_style_profile(
        initialized_client,
        app_with_db,
        initialized_provider,
        project["id"],
        "默认风格",
        _voice_profile("默认短句推进"),
    )
    override_profile = await _create_style_profile(
        initialized_client,
        app_with_db,
        initialized_provider,
        None,
        "覆盖风格",
        _voice_profile("覆盖冷白反问"),
    )

    project_update = await initialized_client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"style_profile_id": default_profile["id"]},
    )
    assert project_update.status_code == 200
    run_response = await initialized_client.post(
        "/api/v1/novel-workflows",
        json={
            "intent_type": "chapter_expand",
            "project_id": project["id"],
            "style_profile_id": override_profile["id"],
            "beats": ["第一拍", "第二拍"],
        },
    )
    assert run_response.status_code == 201

    executor = NovelWorkflowJobExecutor()
    context = await executor._load_run_context(
        app_with_db.state.session_factory,
        run_response.json()["id"],
    )

    assert "覆盖冷白反问" in context.initial_state["style_prompt"]
    assert "默认短句推进" not in context.initial_state["style_prompt"]


@pytest.mark.asyncio
async def test_prompt_stack_manifest_keeps_full_lengths_without_truncation_budget(
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
            username="prompt-stack-full-length-owner",
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
                name="Full Length Stack",
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
                title="Large entry",
                content="X" * 12000,
                keywords=["x"],
                priority=10,
            ),
            user_id=user.id,
        )

        selection = await service.select_for_runtime(
            session,
            project.id,
            user_id=user.id,
            chapter_id=None,
            current_chapter_context="x",
            text_before_cursor="",
        )

    assert "X" * 12000 in selection.prompt_text
    assert selection.manifest.layers[0].char_count >= 12000
    assert selection.manifest.selected_assets[0].char_count == 12000
    dumped = selection.manifest.model_dump(mode="json")
    assert "budget" not in dumped["layers"][0]
    assert "truncated" not in dumped["layers"][0]
    assert "original_char_count" not in dumped["selected_assets"][0]


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


async def _create_style_profile(
    client: AsyncClient,
    app_with_db: FastAPI,
    provider: dict[str, object],
    mount_project_id: str | None,
    style_name: str,
    voice_profile_markdown: str,
) -> dict:
    from app.services.style_analysis_jobs import StyleAnalysisJobService

    job_response = await client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": style_name, "provider_id": str(provider["id"])},
        files={"file": ("sample.txt", "第一章 风雪夜归人".encode("utf-8"), "text/plain")},
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]
    async with app_with_db.state.session_factory() as session:
        await StyleAnalysisJobService().mark_job_succeeded(
            session,
            job_id,
            analysis_meta_payload={
                "source_filename": "sample.txt",
                "model_name": str(provider["default_model"]),
                "text_type": "章节正文",
                "has_timestamps": False,
                "has_speaker_labels": False,
                "has_noise_markers": False,
                "uses_batch_processing": False,
                "location_indexing": "章节或段落位置",
                "chunk_count": 1,
            },
            analysis_report_payload="# 执行摘要\n风格稳定。",
            voice_profile_payload=voice_profile_markdown,
        )
        await session.commit()

    response = await client.post(
        "/api/v1/style-profiles",
        json={
            "job_id": job_id,
            "style_name": style_name,
            "mount_project_id": mount_project_id,
            "voice_profile_markdown": voice_profile_markdown,
        },
    )
    assert response.status_code == 201
    return response.json()


def _voice_profile(marker: str) -> str:
    return (
        "# Voice Profile\n"
        f"## 3.1 口头禅与常用表达\n- 执行规则：{marker}。\n\n"
        "## 3.2 固定句式与节奏偏好\n- 执行规则：长短句交替。\n\n"
        "## 3.3 词汇选择偏好\n- 执行规则：混用现代术语与古典四字格。\n\n"
        "## 3.4 句子构造习惯\n- 执行规则：句首落判断。\n\n"
        "## 3.5 生活经历线索\n- 执行规则：生活线索弱。\n\n"
        "## 3.6 行业／地域词汇\n- 执行规则：行业词偏运营。\n\n"
        "## 3.7 自然化缺陷\n- 执行规则：保留省略和跳接。\n\n"
        "## 3.8 写作忌口与避讳\n- 执行规则：少写解释性开场。\n\n"
        "## 3.9 比喻口味与意象库\n- 执行规则：意象偏月色与视线。\n\n"
        "## 3.10 思维模式与表达逻辑\n- 执行规则：观察、质疑、类比、结论递进。\n\n"
        "## 3.11 常见场景的说话方式\n- 执行规则：对白抢拍试探。\n\n"
        "## 3.12 个人价值取向与反复母题\n- 执行规则：强调效率和掌控。\n"
    )
