from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.services.novel_workflow_storage import NovelWorkflowStorageService


PROMPT_TRACE_ARTIFACT_NAME = "prompt_trace_markdown"
_TRUNCATED_MARKER = "（已按上下文预算截断）"
_OUTPUT_SNIPPET_CHARS = 1200


@dataclass(frozen=True)
class PromptTraceMessage:
    role: str
    content: str


@dataclass(frozen=True)
class PromptTraceCall:
    index: int
    intent_type: str
    stage: str | None
    mode: str
    provider_id: str | None
    provider_label: str | None
    model_name: str | None
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    messages: list[PromptTraceMessage]
    output_char_count: int | None = None
    output_excerpt: str | None = None
    error_summary: str | None = None

    @property
    def total_input_chars(self) -> int:
        return sum(len(message.content) for message in self.messages)

    @property
    def system_char_count(self) -> int:
        return sum(len(message.content) for message in self.messages if message.role == "system")

    @property
    def user_char_count(self) -> int:
        return sum(len(message.content) for message in self.messages if message.role == "user")

    @property
    def has_truncation_marker(self) -> bool:
        return any(_TRUNCATED_MARKER in message.content for message in self.messages)


def build_output_excerpt(output: str) -> str:
    text = output.strip()
    if len(text) <= _OUTPUT_SNIPPET_CHARS * 2:
        return text
    head = text[:_OUTPUT_SNIPPET_CHARS].rstrip()
    tail = text[-_OUTPUT_SNIPPET_CHARS:].lstrip()
    omitted = len(text) - len(head) - len(tail)
    return f"{head}\n\n...[omitted {omitted} chars]...\n\n{tail}"


def render_prompt_trace_markdown(*, run_id: str, calls: list[PromptTraceCall]) -> str:
    total_input_chars = sum(call.total_input_chars for call in calls)
    completed_calls = [call for call in calls if call.completed_at is not None]
    failed_calls = [call for call in calls if call.error_summary]
    lines: list[str] = [
        "# Prompt Trace",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Run ID | `{_escape_table(run_id)}` |",
        f"| Calls | {len(calls)} |",
        f"| Completed calls | {len(completed_calls)} |",
        f"| Failed calls | {len(failed_calls)} |",
        f"| Total input chars | {total_input_chars} |",
        f"| Contains truncation marker | {_format_bool(any(call.has_truncation_marker for call in calls))} |",
        "",
    ]
    if not calls:
        lines.extend(["No LLM calls recorded yet.", ""])
        return "\n".join(lines)

    lines.extend(
        [
            "## Call summary",
            "",
            "| # | Stage | Mode | Model | Input chars | Output chars | Truncated | Error |",
            "| --- | --- | --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for call in calls:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(call.index),
                    _escape_table(call.stage or "-"),
                    _escape_table(call.mode),
                    _escape_table(call.model_name or "-"),
                    str(call.total_input_chars),
                    str(call.output_char_count if call.output_char_count is not None else "-"),
                    _format_bool(call.has_truncation_marker),
                    _escape_table(call.error_summary or "-"),
                ]
            )
            + " |"
        )
    lines.append("")

    for call in calls:
        lines.extend(_render_call(call))
    return "\n".join(lines).rstrip() + "\n"


class PromptTraceRecorder:
    def __init__(
        self,
        *,
        run_id: str,
        intent_type: str,
        provider_id: str | None,
        provider_label: str | None,
        model_name: str | None,
        storage_service: NovelWorkflowStorageService,
        stage_getter: object,
    ) -> None:
        self.run_id = run_id
        self.intent_type = intent_type
        self.provider_id = provider_id
        self.provider_label = provider_label
        self.model_name = model_name
        self.storage_service = storage_service
        self.stage_getter = stage_getter
        self._calls: list[PromptTraceCall] = []

    async def record_success(
        self,
        *,
        mode: str,
        messages: list[PromptTraceMessage],
        started_at: datetime,
        completed_at: datetime,
        output: str,
    ) -> None:
        self._calls.append(
            PromptTraceCall(
                index=len(self._calls) + 1,
                intent_type=self.intent_type,
                stage=self._stage(),
                mode=mode,
                provider_id=self.provider_id,
                provider_label=self.provider_label,
                model_name=self.model_name,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=_duration_ms(started_at, completed_at),
                messages=messages,
                output_char_count=len(output),
                output_excerpt=build_output_excerpt(output),
            )
        )
        await self.flush()

    async def record_error(
        self,
        *,
        mode: str,
        messages: list[PromptTraceMessage],
        started_at: datetime,
        completed_at: datetime,
        error_summary: str,
    ) -> None:
        self._calls.append(
            PromptTraceCall(
                index=len(self._calls) + 1,
                intent_type=self.intent_type,
                stage=self._stage(),
                mode=mode,
                provider_id=self.provider_id,
                provider_label=self.provider_label,
                model_name=self.model_name,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=_duration_ms(started_at, completed_at),
                messages=messages,
                error_summary=error_summary,
            )
        )
        await self.flush()

    async def flush(self) -> None:
        await self.storage_service.write_stage_markdown_artifact(
            self.run_id,
            name=PROMPT_TRACE_ARTIFACT_NAME,
            markdown=render_prompt_trace_markdown(run_id=self.run_id, calls=self._calls),
        )

    def _stage(self) -> str | None:
        if callable(self.stage_getter):
            return self.stage_getter()
        return None


def _render_call(call: PromptTraceCall) -> list[str]:
    title_stage = call.stage or "unknown-stage"
    lines: list[str] = [
        f"## Call {call.index} - {title_stage} / {call.mode}",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Intent | `{_escape_table(call.intent_type)}` |",
        f"| Stage | `{_escape_table(call.stage or '-')}` |",
        f"| Mode | `{_escape_table(call.mode)}` |",
        f"| Provider | `{_escape_table(call.provider_label or '-')}` |",
        f"| Provider ID | `{_escape_table(call.provider_id or '-')}` |",
        f"| Model | `{_escape_table(call.model_name or '-')}` |",
        f"| Started at | `{call.started_at.isoformat(timespec='milliseconds')}` |",
        f"| Completed at | `{call.completed_at.isoformat(timespec='milliseconds') if call.completed_at else '-'}` |",
        f"| Duration | {call.duration_ms if call.duration_ms is not None else '-'} ms |",
        f"| Total input chars | {call.total_input_chars} |",
        f"| System chars | {call.system_char_count} |",
        f"| User chars | {call.user_char_count} |",
        f"| Output chars | {call.output_char_count if call.output_char_count is not None else '-'} |",
        f"| Contains truncation marker | {_format_bool(call.has_truncation_marker)} |",
    ]
    if call.error_summary:
        lines.append(f"| Error | `{_escape_table(call.error_summary)}` |")
    lines.append("")

    for message in call.messages:
        label = message.role.capitalize()
        lines.extend(
            [
                f"### {label} message",
                "",
                f"- Chars: {len(message.content)}",
                f"- Contains truncation marker: {_format_bool(_TRUNCATED_MARKER in message.content)}",
                "",
                _fenced_code_block(message.content),
                "",
            ]
        )

    lines.extend(["### Output excerpt", ""])
    if call.output_excerpt:
        lines.extend([_fenced_code_block(call.output_excerpt), ""])
    elif call.error_summary:
        lines.extend([f"Call failed before producing output: `{call.error_summary}`", ""])
    else:
        lines.extend(["No output captured.", ""])
    return lines


def _fenced_code_block(content: str) -> str:
    current = 0
    longest = 0
    for char in content:
        if char == "`":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    fence = "`" * max(3, longest + 1)
    return f"{fence}\n{content}\n{fence}"


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _format_bool(value: bool) -> str:
    return "yes" if value else "no"


def _duration_ms(started_at: datetime, completed_at: datetime) -> int:
    return max(0, int((completed_at - started_at).total_seconds() * 1000))
