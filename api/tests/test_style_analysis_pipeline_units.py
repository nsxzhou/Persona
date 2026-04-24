from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
import httpx
from openai import PermissionDeniedError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    ChunkAnalysis,
    MergedAnalysis,
    STYLE_ANALYSIS_REPORT_SECTIONS,
)
from app.services import llm_model_factory as llm_model_factory_module
from app.services.llm_provider import LLMProviderService
from app.services.prompt_injection import INNER_OS_MARKER, NO_INNER_OS_MARKER
from app.services.style_analysis_llm import EmptyMarkdownResponseError, MarkdownLLMClient
from app.services.style_analysis_storage import StyleAnalysisStorageService
from app.services.style_analysis_text import read_chunks_and_classification
from app.services.style_analysis_pipeline import StyleAnalysisPipeline


def build_chunk_markdown(label: str) -> str:
    return f"# 执行摘要\n{label}\n\n## 3.1 口头禅与常用表达\n- 夜色很冷。\n"


def test_style_analysis_report_sections_cover_expected_titles_in_order() -> None:
    assert STYLE_ANALYSIS_REPORT_SECTIONS == [
        ("3.1", "口头禅与常用表达"),
        ("3.2", "固定句式与节奏偏好"),
        ("3.3", "词汇选择偏好"),
        ("3.4", "句子构造习惯"),
        ("3.5", "生活经历线索"),
        ("3.6", "行业／地域词汇"),
        ("3.7", "自然化缺陷"),
        ("3.8", "写作忌口与避讳"),
        ("3.9", "比喻口味与意象库"),
        ("3.10", "思维模式与表达逻辑"),
        ("3.11", "常见场景的说话方式"),
        ("3.12", "个人价值取向与反复母题"),
    ]


def test_chunk_and_merged_analysis_accept_markdown_payloads() -> None:
    chunk = ChunkAnalysis.model_validate(
        {"chunk_index": 0, "chunk_count": 1, "markdown": build_chunk_markdown("chunk")}
    )
    merged = MergedAnalysis.model_validate(
        {"classification": {"text_type": "章节正文"}, "markdown": build_chunk_markdown("merged")}
    )

    assert chunk.markdown.startswith("# 执行摘要")
    assert "## 3.1 口头禅与常用表达" in merged.markdown
    assert merged.classification.text_type == "章节正文"
    assert merged.classification.noise_notes == "未发现显著噪声。"


def test_analysis_meta_requires_expected_fields() -> None:
    meta = AnalysisMeta.model_validate(
        {
            "source_filename": "sample.txt",
            "model_name": "gpt-5.4",
            "text_type": "章节正文",
            "has_timestamps": False,
            "has_speaker_labels": False,
            "has_noise_markers": False,
            "uses_batch_processing": True,
            "location_indexing": "章节或段落位置",
            "chunk_count": 3,
        }
    )
    assert meta.chunk_count == 3
    with pytest.raises(ValidationError):
        AnalysisMeta.model_validate({"source_filename": "sample.txt"})


def test_settings_reject_invalid_worker_interval_and_chunk_concurrency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import Settings

    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")

    with pytest.raises(ValidationError):
        Settings(PERSONA_STYLE_ANALYSIS_POLL_INTERVAL_SECONDS="0")

    with pytest.raises(ValidationError):
        Settings(PERSONA_STYLE_ANALYSIS_CHUNK_MAX_CONCURRENCY="0")

    with pytest.raises(ValidationError):
        Settings(PERSONA_STYLE_ANALYSIS_CHUNK_MAX_CONCURRENCY="128")


@pytest.mark.asyncio
async def test_structured_llm_client_extracts_markdown_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    monkeypatch.setenv("PERSONA_LLM_TIMEOUT_SECONDS", "12.5")
    get_settings.cache_clear()

    class FakeModel:
        async def ainvoke(self, messages: list[HumanMessage]) -> AIMessage:
            assert len(messages) == 1
            assert str(messages[0].content).startswith("生成报告")
            assert NO_INNER_OS_MARKER in str(messages[0].content)
            return AIMessage(content="# 标题\n正文")

    provider = SimpleNamespace(
        base_url="https://api.example.test/v1",
        api_key_encrypted="encrypted-key",
    )
    factory_calls: list[dict] = []

    def fake_model_factory(**kwargs: object) -> FakeModel:
        factory_calls.append(kwargs)
        return FakeModel()

    client = MarkdownLLMClient(
        model_factory=fake_model_factory,
        secret_decrypter=lambda value: f"decrypted:{value}",
    )
    model = client.build_model(provider=provider, model_name="gpt-4.1-mini")
    result = await client.ainvoke_markdown(model=model, prompt="生成报告")

    assert result == "# 标题\n正文"
    assert factory_calls == [
        {
            "model": "gpt-4.1-mini",
            "model_provider": "openai",
            "base_url": "https://api.example.test/v1",
            "api_key": "decrypted:encrypted-key",
            "temperature": 0.0,
            "timeout": 12.5,
            "max_retries": 2,
        }
    ]
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_markdown_llm_client_supports_injection_modes() -> None:
    seen_prompts: list[str] = []

    class FakeModel:
        async def ainvoke(self, messages: list[HumanMessage]) -> AIMessage:
            seen_prompts.append(str(messages[0].content))
            return AIMessage(content="# OK")

    model = FakeModel()
    client = MarkdownLLMClient(model_factory=lambda **_: model, secret_decrypter=lambda value: value)

    await client.ainvoke_markdown(model=model, prompt="分析任务")
    await client.ainvoke_markdown(model=model, prompt="正文任务", injection_mode="immersion")
    await client.ainvoke_markdown(model=model, prompt="连接测试", injection_mode="none")

    assert NO_INNER_OS_MARKER in seen_prompts[0]
    assert INNER_OS_MARKER in seen_prompts[1]
    assert seen_prompts[2] == "连接测试"


@pytest.mark.asyncio
async def test_llm_provider_service_injects_markers_into_first_human_message() -> None:
    captured_messages: list[list[object]] = []

    class FakeModel:
        async def ainvoke(self, messages: list[object]) -> AIMessage:
            captured_messages.append(messages)
            return AIMessage(content="OK")

        async def astream(self, messages: list[object]):
            captured_messages.append(messages)
            if False:
                yield AIMessage(content="")

    provider = SimpleNamespace()
    service = LLMProviderService()
    service._build_model = lambda *args, **kwargs: FakeModel()  # type: ignore[method-assign]

    await service.invoke_completion(provider, "system", "分析")
    await service.invoke_completion(provider, "system", "正文", injection_mode="immersion")
    await service.invoke_completion(provider, "system", "无注入", injection_mode="none")
    async for _ in service.stream_messages(
        provider,
        [SystemMessage(content="system"), HumanMessage(content="流式")],
    ):
        pass

    assert NO_INNER_OS_MARKER in str(captured_messages[0][1].content)
    assert INNER_OS_MARKER in str(captured_messages[1][1].content)
    assert str(captured_messages[2][1].content) == "无注入"
    assert NO_INNER_OS_MARKER in str(captured_messages[3][1].content)


def test_llm_provider_service_uses_configured_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    monkeypatch.setenv("PERSONA_LLM_TIMEOUT_SECONDS", "7.5")
    get_settings.cache_clear()

    factory_calls: list[dict] = []

    def fake_init_chat_model(**kwargs: object) -> object:
        factory_calls.append(kwargs)
        return object()

    monkeypatch.setattr(llm_model_factory_module, "init_chat_model", fake_init_chat_model)
    monkeypatch.setattr(
        llm_model_factory_module,
        "decrypt_secret",
        lambda value: f"decrypted:{value}",
    )

    provider = SimpleNamespace(
        base_url="https://api.example.test/v1",
        api_key_encrypted="encrypted-key",
        default_model="gpt-4.1-mini",
    )

    service = LLMProviderService()
    service._build_model(provider)

    assert factory_calls == [
        {
            "model": "gpt-4.1-mini",
            "model_provider": "openai",
            "base_url": "https://api.example.test/v1",
            "api_key": "decrypted:encrypted-key",
            "temperature": 0.7,
            "timeout": 7.5,
            "max_retries": 2,
        }
    ]
    get_settings.cache_clear()


def test_markdown_llm_client_and_provider_service_share_model_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    get_settings.cache_clear()

    factory_calls: list[dict] = []

    def fake_init_chat_model(**kwargs: object) -> object:
        factory_calls.append(kwargs)
        return object()

    monkeypatch.setattr(llm_model_factory_module, "init_chat_model", fake_init_chat_model)
    monkeypatch.setattr(llm_model_factory_module, "decrypt_secret", lambda value: f"decrypted:{value}")

    provider = SimpleNamespace(
        base_url="https://api.example.test/v1",
        api_key_encrypted="encrypted-key",
        default_model="gpt-4.1-mini",
    )

    LLMProviderService()._build_model(provider, temperature=0.2)
    MarkdownLLMClient().build_model(provider=provider, model_name="gpt-4.1-mini")

    assert factory_calls == [
        {
            "model": "gpt-4.1-mini",
            "model_provider": "openai",
            "base_url": "https://api.example.test/v1",
            "api_key": "decrypted:encrypted-key",
            "temperature": 0.2,
            "timeout": 300.0,
            "max_retries": 2,
        },
        {
            "model": "gpt-4.1-mini",
            "model_provider": "openai",
            "base_url": "https://api.example.test/v1",
            "api_key": "decrypted:encrypted-key",
            "temperature": 0.0,
            "timeout": 300.0,
            "max_retries": 2,
        },
    ]
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_structured_llm_client_extracts_markdown_from_nonstandard_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    get_settings.cache_clear()

    class FakeModel:
        def __init__(self) -> None:
            self.calls = 0

        async def ainvoke(self, messages: list[HumanMessage]) -> AIMessage:
            self.calls += 1
            assert len(messages) == 1
            if self.calls == 1:
                return AIMessage(
                    content="",
                    additional_kwargs={"content": "# 兼容字段\n正文"},
                )
            return AIMessage(
                content="",
                additional_kwargs={"output_text": "# 输出文本\n正文"},
            )

    model = FakeModel()
    client = MarkdownLLMClient(model_factory=lambda **_: model, secret_decrypter=lambda value: value)

    result_from_content = await client.ainvoke_markdown(model=model, prompt="第一次")
    result_from_output_text = await client.ainvoke_markdown(model=model, prompt="第二次")

    assert result_from_content == "# 兼容字段\n正文"
    assert result_from_output_text == "# 输出文本\n正文"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_structured_llm_client_uses_reasoning_content_as_last_resort(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    get_settings.cache_clear()

    class FakeModel:
        async def ainvoke(self, messages: list[HumanMessage]) -> AIMessage:
            assert len(messages) == 1
            return AIMessage(
                content="",
                additional_kwargs={"reasoning_content": "# 推理兜底\n正文"},
                response_metadata={"finish_reason": "stop"},
            )

    model = FakeModel()
    client = MarkdownLLMClient(model_factory=lambda **_: model, secret_decrypter=lambda value: value)

    with caplog.at_level("WARNING", logger="app.services.style_analysis_llm"):
        result = await client.ainvoke_markdown(model=model, prompt="生成报告")

    assert result == "# 推理兜底\n正文"
    assert "Recovered markdown from reasoning_content fallback" in caplog.text
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_structured_llm_client_retries_empty_response_until_markdown_arrives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    get_settings.cache_clear()

    class FakeModel:
        def __init__(self) -> None:
            self.calls = 0

        async def ainvoke(self, messages: list[HumanMessage]) -> AIMessage:
            self.calls += 1
            assert len(messages) == 1
            if self.calls < 3:
                return AIMessage(
                    content="",
                    response_metadata={
                        "finish_reason": "stop",
                        "token_usage": {"completion_tokens": 128},
                    },
                )
            return AIMessage(content="# 最终成功\n正文")

    async def fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    model = FakeModel()
    client = MarkdownLLMClient(model_factory=lambda **_: model, secret_decrypter=lambda value: value)
    result = await client.ainvoke_markdown(model=model, prompt="生成报告")

    assert result == "# 最终成功\n正文"
    assert model.calls == 3
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_structured_llm_client_retries_retryable_forbidden_gateway_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    get_settings.cache_clear()

    class FakeModel:
        def __init__(self) -> None:
            self.calls = 0

        async def ainvoke(self, messages: list[HumanMessage]) -> AIMessage:
            self.calls += 1
            assert len(messages) == 1
            if self.calls < 3:
                request = httpx.Request("POST", "https://api.example.test/v1/chat/completions")
                response = httpx.Response(
                    403,
                    request=request,
                    json={"error": {"message": "Forbidden", "type": "api_error"}},
                )
                raise PermissionDeniedError(
                    "Error code: 403 - {'error': {'message': 'Forbidden', 'type': 'api_error'}}",
                    response=response,
                    body=response.json(),
                )
            return AIMessage(content="# 最终成功\n正文")

    async def fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    model = FakeModel()
    client = MarkdownLLMClient(model_factory=lambda **_: model, secret_decrypter=lambda value: value)
    result = await client.ainvoke_markdown(model=model, prompt="生成报告")

    assert result == "# 最终成功\n正文"
    assert model.calls == 3
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_structured_llm_client_retries_malformed_responses_until_markdown_arrives(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    get_settings.cache_clear()

    class FakeModel:
        def __init__(self) -> None:
            self.calls = 0

        async def ainvoke(self, messages: list[HumanMessage]) -> AIMessage:
            self.calls += 1
            assert len(messages) == 1
            if self.calls == 1:
                raise AttributeError("'NoneType' object has no attribute 'model_dump'")
            if self.calls == 2:
                raise TypeError("Received response with null value for 'choices'.")
            return AIMessage(content="# 最终成功\n正文")

    async def fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    model = FakeModel()
    provider = SimpleNamespace(
        base_url="https://api.example.test/v1",
        api_key_encrypted="encrypted-key",
    )
    client = MarkdownLLMClient(
        model_factory=lambda **_: model,
        secret_decrypter=lambda value: value,
    )

    with caplog.at_level("WARNING", logger="app.services.style_analysis_llm"):
        result = await client.ainvoke_markdown(
            model=model,
            prompt="生成报告",
            provider=provider,
            model_name="gpt-4.1-mini",
        )

    assert result == "# 最终成功\n正文"
    assert model.calls == 3
    assert "malformed response" in caplog.text.lower()
    assert caplog.text.lower().count("malformed response") == 2
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_structured_llm_client_raises_empty_markdown_error_after_exhausting_malformed_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    get_settings.cache_clear()

    class FakeModel:
        def __init__(self) -> None:
            self.calls = 0

        async def ainvoke(self, messages: list[HumanMessage]) -> AIMessage:
            self.calls += 1
            assert len(messages) == 1
            raise AttributeError("'NoneType' object has no attribute 'model_dump'")

    async def fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    model = FakeModel()
    client = MarkdownLLMClient(model_factory=lambda **_: model, secret_decrypter=lambda value: value)

    with pytest.raises(EmptyMarkdownResponseError) as exc_info:
        await client.ainvoke_markdown(
            model=model,
            prompt="生成报告",
            provider=SimpleNamespace(base_url="https://api.example.test/v1"),
            model_name="gpt-4.1-mini",
        )

    message = str(exc_info.value)
    assert "malformed_response" in message
    assert "attempt=3/3" in message
    assert model.calls == 3
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_structured_llm_client_raises_diagnostic_error_when_all_attempts_are_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    get_settings.cache_clear()

    class FakeModel:
        def __init__(self) -> None:
            self.calls = 0

        async def ainvoke(self, messages: list[HumanMessage]) -> AIMessage:
            self.calls += 1
            assert len(messages) == 1
            return AIMessage(
                content="",
                response_metadata={
                    "finish_reason": "stop",
                    "token_usage": {"completion_tokens": 1449, "prompt_tokens": 1575},
                },
            )

    async def fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    model = FakeModel()
    client = MarkdownLLMClient(model_factory=lambda **_: model, secret_decrypter=lambda value: value)

    with pytest.raises(EmptyMarkdownResponseError) as exc_info:
        await client.ainvoke_markdown(model=model, prompt="不要泄漏这段 prompt")

    message = str(exc_info.value)
    assert "attempt=3/3" in message
    assert "finish_reason=stop" in message
    assert "completion_tokens=1449" in message
    assert "不要泄漏这段 prompt" not in message
    assert model.calls == 3
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_storage_service_batches_chunk_analysis_artifacts_and_cleans_job_artifacts(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    storage_service = StyleAnalysisStorageService()
    job_id = "job-artifacts"

    await storage_service.write_chunk_artifact(job_id, 0, "chunk-0")
    await storage_service.write_chunk_artifact(job_id, 1, "chunk-1")
    await storage_service.write_chunk_artifact(job_id, 2, "chunk-2")
    assert await storage_service.read_chunk_artifact(job_id, 1) == "chunk-1"

    for index in range(3):
        await storage_service.write_chunk_analysis_artifact(
            job_id,
            index,
            {
                "chunk_index": index,
                "chunk_count": 3,
                "markdown": build_chunk_markdown(f"chunk-{index}"),
            },
        )

    batches = [
        batch
        async for batch in storage_service.read_chunk_analysis_batches(
            job_id,
            batch_size=2,
        )
    ]

    assert [[item["chunk_index"] for item in batch] for batch in batches] == [[0, 1], [2]]

    await storage_service.cleanup_job_artifacts(job_id)
    assert await storage_service.job_artifacts_exist(job_id) is False
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_storage_cleanup_uses_asyncio_to_thread(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    storage_service = StyleAnalysisStorageService()
    job_id = "job-cleanup-thread"
    await storage_service.write_chunk_artifact(job_id, 0, "chunk-0")
    assert await storage_service.job_artifacts_exist(job_id) is True

    called: list[tuple[object, tuple, dict]] = []

    async def fake_to_thread(func, /, *args, **kwargs):
        called.append((func, args, kwargs))
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    await storage_service.cleanup_job_artifacts(job_id)

    assert called
    assert await storage_service.job_artifacts_exist(job_id) is False
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_read_chunks_and_classification_streams_chunks_via_callback() -> None:
    emitted_chunks: list[tuple[int, str]] = []

    async def stream():
        content = (
            "第一章 开始\n"
            + "这是一段测试文字，用于凑够字数以便触发发射。" * 5 + "\n"
            + "第二章 继续\n"
            + "这是第二段测试文字，用于凑够字数以便触发发射。" * 5 + "\n"
            + "第三章 结束\n"
            + "这是第三段测试文字，用于凑够字数以便触发发射。" * 5
        )
        yield content.encode("utf-8")

    async def on_chunk(index: int, chunk_text: str) -> None:
        emitted_chunks.append((index, chunk_text))

    chunk_count, _character_count, classification = await read_chunks_and_classification(
        stream(),
        on_chunk=on_chunk,
    )

    assert chunk_count == 3
    assert classification["location_indexing"] == "章节或段落位置"


@pytest.mark.asyncio
async def test_pipeline_merge_chunks_reduces_batches_incrementally() -> None:
    class FakeStorageService:
        def stage_markdown_artifact_exists(self, job_id: str, *, name: str) -> bool:
            del job_id, name
            return False

        async def append_job_log(self, job_id: str, message: str) -> None:
            pass

        async def read_chunk_analysis_batches(self, job_id: str, *, batch_size: int):
            del job_id, batch_size
            yield [
                {"chunk_index": 0, "chunk_count": 10, "markdown": build_chunk_markdown("0")},
                {"chunk_index": 1, "chunk_count": 10, "markdown": build_chunk_markdown("1")},
            ]
            yield [
                {"chunk_index": 2, "chunk_count": 10, "markdown": build_chunk_markdown("2")},
                {"chunk_index": 3, "chunk_count": 10, "markdown": build_chunk_markdown("3")},
            ]

        async def write_stage_markdown_artifact(
            self, job_id: str, *, name: str, markdown: str
        ) -> None:
            del job_id, name, markdown

    class FakeMergeClient:
        def __init__(self) -> None:
            self.merge_calls = 0

        def build_model(self, *, provider: object, model_name: str) -> object:
            return SimpleNamespace(provider=provider, model_name=model_name)

        async def ainvoke_markdown(
            self,
            *,
            model: object,
            prompt: str,
            provider: object | None = None,
            model_name: str | None = None,
        ) -> str:
            del model, prompt, provider, model_name
            self.merge_calls += 1
            return build_chunk_markdown(f"merge-{self.merge_calls}")

    client = FakeMergeClient()
    pipeline = StyleAnalysisPipeline(
        provider=SimpleNamespace(base_url="https://api.example.test/v1", api_key_encrypted="encrypted"),
        model_name="gpt-4.1-mini",
        style_name="古龙风格实验",
        source_filename="sample.txt",
        llm_client=client,
    )
    pipeline.storage_service = FakeStorageService()

    merged = await pipeline._merge_chunks(
        {
            "job_id": "job-merge",
            "style_name": "古龙风格实验",
            "source_filename": "sample.txt",
            "model_name": "gpt-4.1-mini",
            "chunk_count": 4,
            "classification": {
                "text_type": "章节正文",
                "has_timestamps": False,
                "has_speaker_labels": False,
                "has_noise_markers": False,
                "uses_batch_processing": True,
                "location_indexing": "章节或段落位置",
                "noise_notes": "未发现显著噪声。",
            },
        }
    )

    assert client.merge_calls == 2
    assert merged["merged_analysis_markdown"].startswith("# 执行摘要")


@pytest.mark.asyncio
async def test_style_pipeline_sets_postprocessing_stage_for_summary_and_prompt_pack() -> None:
    seen_stages: list[str | None] = []

    class FakeClient:
        def build_model(self, *, provider: object, model_name: str) -> object:
            return SimpleNamespace(provider=provider, model_name=model_name)

        async def ainvoke_markdown(
            self,
            *,
            model: object,
            prompt: str,
            provider: object | None = None,
            model_name: str | None = None,
        ) -> str:
            del model, provider, model_name
            if "可编辑风格摘要" in prompt:
                return "# 风格名称\n古龙风格实验\n"
            if "全局可复用的 Markdown 风格母 prompt 包" in prompt:
                return "# System Prompt\n保持冷峻克制\n"
            raise AssertionError(f"unexpected prompt: {prompt[:80]}")

    pipeline = StyleAnalysisPipeline(
        provider=SimpleNamespace(base_url="https://api.example.test/v1", api_key_encrypted="encrypted"),
        model_name="gpt-4.1-mini",
        style_name="古龙风格实验",
        source_filename="sample.txt",
        llm_client=FakeClient(),
        stage_callback=lambda stage: seen_stages.append(stage) or asyncio.sleep(0),
    )

    state = {
        "job_id": "job-style-post",
        "style_name": "古龙风格实验",
        "source_filename": "sample.txt",
        "model_name": "gpt-4.1-mini",
        "chunk_count": 2,
        "classification": {
            "text_type": "章节正文",
            "has_timestamps": False,
            "has_speaker_labels": False,
            "has_noise_markers": False,
            "uses_batch_processing": True,
            "location_indexing": "章节或段落位置",
            "noise_notes": "未发现显著噪声。",
        },
        "analysis_report_markdown": "# 执行摘要\n报告\n",
        "style_summary_markdown": "# 风格名称\n旧值\n",
    }

    summary_result = await pipeline._build_summary(state)
    prompt_result = await pipeline._build_prompt_pack({**state, **summary_result})

    assert summary_result["style_summary_markdown"].startswith("# 风格名称")
    assert prompt_result["prompt_pack_markdown"].startswith("# System Prompt")
    assert seen_stages == ["postprocessing", "postprocessing"]
