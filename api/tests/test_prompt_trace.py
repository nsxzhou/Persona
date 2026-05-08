from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services.prompt_trace import (
    PromptTraceCall,
    PromptTraceMessage,
    build_output_excerpt,
    render_prompt_trace_markdown,
)


def test_prompt_trace_renderer_handles_multiple_calls_fences_and_errors() -> None:
    started = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
    calls = [
        PromptTraceCall(
            index=1,
            intent_type="selection_rewrite",
            stage="generating",
            mode="immersion",
            provider_id="provider-1",
            provider_label="Primary",
            model_name="gpt-test",
            started_at=started,
            completed_at=started + timedelta(milliseconds=42),
            duration_ms=42,
            messages=[
                PromptTraceMessage("system", "系统提示"),
                PromptTraceMessage("user", "包含 fence:\n```python\nprint(1)\n```"),
            ],
            provider_prompt_override_applied=True,
            output_char_count=2,
            output_excerpt="OK",
        ),
        PromptTraceCall(
            index=2,
            intent_type="selection_rewrite",
            stage="generating",
            mode="analysis",
            provider_id="provider-1",
            provider_label="Primary",
            model_name="gpt-test",
            started_at=started,
            completed_at=started + timedelta(milliseconds=10),
            duration_ms=10,
            messages=[PromptTraceMessage("user", "（已按上下文预算截断）")],
            error_summary="boom",
        ),
    ]

    markdown = render_prompt_trace_markdown(run_id="run-1", calls=calls)

    assert "# Prompt Trace" in markdown
    assert "| Calls | 2 |" in markdown
    assert "| Failed calls | 1 |" in markdown
    assert "## Call 1 - generating / immersion" in markdown
    assert "## Call 2 - generating / analysis" in markdown
    assert "| Provider prompt override | yes |" in markdown
    assert "| Provider prompt override | no |" in markdown
    assert "````" in markdown
    assert "boom" in markdown
    assert "| Contains truncation marker | yes |" in markdown


def test_prompt_trace_renderer_includes_prompt_stack_manifest() -> None:
    started = datetime(2026, 5, 8, 10, 0, tzinfo=UTC)
    markdown = render_prompt_trace_markdown(
        run_id="run-stack",
        calls=[
            PromptTraceCall(
                index=1,
                intent_type="beat_expand",
                stage="generating",
                mode="immersion",
                provider_id="provider-1",
                provider_label="Primary",
                model_name="gpt-test",
                started_at=started,
                completed_at=started,
                duration_ms=0,
                messages=[PromptTraceMessage("system", "SYSTEM")],
                prompt_stack_manifest={
                    "layers": [
                        {
                            "key": "active_lorebook_entries",
                            "title": "Active Lorebook Entries",
                            "char_count": 120,
                            "assets": [{"id": "asset-1", "title": "River city"}],
                        }
                    ],
                    "selected_assets": [
                        {
                            "id": "asset-1",
                            "title": "River city",
                            "kind": "lorebook_entry",
                            "priority": 5,
                            "char_count": 80,
                            "match_reasons": ["keyword"],
                            "matched_keywords": ["river"],
                        }
                    ],
                },
                output_char_count=2,
                output_excerpt="OK",
            )
        ],
    )

    assert "### Prompt Stack Manifest" in markdown
    assert "Active Lorebook Entries" in markdown
    assert "River city" in markdown
    assert "keyword" in markdown
    assert "Budget" not in markdown


def test_prompt_trace_output_excerpt_keeps_head_and_tail() -> None:
    output = "A" * 1300 + "MIDDLE" + "Z" * 1300

    excerpt = build_output_excerpt(output)

    assert excerpt.startswith("A" * 100)
    assert excerpt.endswith("Z" * 100)
    assert "omitted" in excerpt
    assert "MIDDLE" not in excerpt


@pytest.mark.asyncio
async def test_invoke_completion_trace_callback_receives_injected_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.llm_provider import LLMProviderService

    class FakeModel:
        async def ainvoke(self, messages):  # type: ignore[no-untyped-def]
            self.messages = messages
            return SimpleNamespace(content="done")

    fake_model = FakeModel()
    service = LLMProviderService()
    monkeypatch.setattr(service, "_build_model", lambda *_, **__: fake_model)
    traces = []

    async def trace_callback(**payload):  # type: ignore[no-untyped-def]
        traces.append(payload)

    result = await service.invoke_completion(
        provider_config=SimpleNamespace(
            immersion_prompt_override_enabled=False,
            immersion_system_prompt_suffix="",
        ),
        system_prompt="SYSTEM",
        user_context="USER",
        injection_mode="analysis",
        prompt_trace_callback=trace_callback,
    )

    assert result == "done"
    assert len(traces) == 1
    messages = traces[0]["messages"]
    assert messages[0].role == "system"
    assert messages[0].content == "SYSTEM"
    assert messages[1].role == "user"
    assert messages[1].content.startswith("USER")
    assert "规划方式要求" in messages[1].content
    assert "<think>" not in messages[1].content
    assert traces[0]["provider_prompt_override_applied"] is False


@pytest.mark.asyncio
async def test_invoke_completion_appends_provider_override_only_for_immersion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.llm_provider import LLMProviderService

    class FakeModel:
        def __init__(self) -> None:
            self.calls = []

        async def ainvoke(self, messages):  # type: ignore[no-untyped-def]
            self.calls.append(messages)
            return SimpleNamespace(content="done")

    fake_model = FakeModel()
    service = LLMProviderService()
    monkeypatch.setattr(service, "_build_model", lambda *_, **__: fake_model)
    traces = []
    provider = SimpleNamespace(
        immersion_prompt_override_enabled=True,
        immersion_system_prompt_suffix="Provider suffix",
    )

    async def trace_callback(**payload):  # type: ignore[no-untyped-def]
        traces.append(payload)

    await service.invoke_completion(
        provider_config=provider,
        system_prompt="SYSTEM",
        user_context="USER",
        injection_mode="immersion",
        prompt_trace_callback=trace_callback,
    )
    await service.invoke_completion(
        provider_config=provider,
        system_prompt="SYSTEM",
        user_context="USER",
        injection_mode="analysis",
        prompt_trace_callback=trace_callback,
    )
    await service.invoke_completion(
        provider_config=provider,
        system_prompt="SYSTEM",
        user_context="USER",
        injection_mode="none",
        prompt_trace_callback=trace_callback,
    )

    assert fake_model.calls[0][0].content == "SYSTEM\n\nProvider suffix"
    assert "正文沉浸要求" in fake_model.calls[0][1].content
    assert traces[0]["provider_prompt_override_applied"] is True

    assert fake_model.calls[1][0].content == "SYSTEM"
    assert "规划方式要求" in fake_model.calls[1][1].content
    assert "<think>" not in fake_model.calls[1][1].content
    assert traces[1]["provider_prompt_override_applied"] is False

    assert fake_model.calls[2][0].content == "SYSTEM"
    assert fake_model.calls[2][1].content == "USER"
    assert traces[2]["provider_prompt_override_applied"] is False


@pytest.mark.asyncio
async def test_invoke_completion_ignores_blank_provider_override_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.llm_provider import LLMProviderService

    class FakeModel:
        async def ainvoke(self, messages):  # type: ignore[no-untyped-def]
            self.messages = messages
            return SimpleNamespace(content="done")

    fake_model = FakeModel()
    service = LLMProviderService()
    monkeypatch.setattr(service, "_build_model", lambda *_, **__: fake_model)
    traces = []

    async def trace_callback(**payload):  # type: ignore[no-untyped-def]
        traces.append(payload)

    await service.invoke_completion(
        provider_config=SimpleNamespace(
            immersion_prompt_override_enabled=True,
            immersion_system_prompt_suffix="   ",
        ),
        system_prompt="SYSTEM",
        user_context="USER",
        injection_mode="immersion",
        prompt_trace_callback=trace_callback,
    )

    assert fake_model.messages[0].content == "SYSTEM"
    assert traces[0]["provider_prompt_override_applied"] is False
