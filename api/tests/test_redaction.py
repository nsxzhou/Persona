from __future__ import annotations


def test_redact_sensitive_text_masks_tokens() -> None:
    from app.core.redaction import redact_sensitive_text

    assert redact_sensitive_text("sk-abcdef123456") == "[REDACTED]"
    assert redact_sensitive_text("Authorization: Bearer abc.def.ghi") == "Authorization: Bearer [REDACTED]"
    assert (
        redact_sensitive_text("https://example.com/v1?api_key=sk-abcdef123456&x=1")
        == "https://example.com/v1?api_key=[REDACTED]&x=1"
    )
    assert redact_sensitive_text("api_key=sk-abcdef123456") == "api_key=[REDACTED]"


def test_summarize_exception_includes_type_and_is_truncated() -> None:
    from app.core.redaction import summarize_exception

    exc = RuntimeError("x" * 1000)
    summary = summarize_exception(exc, max_len=40)
    assert summary.startswith("RuntimeError: ")
    assert len(summary) <= 40
