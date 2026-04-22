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


def test_style_analysis_error_sanitizer_redacts_sensitive_tokens() -> None:
    from app.services.style_analysis_jobs import sanitize_style_analysis_error_message

    message = "provider rejected token sk-secret123456 with Authorization: Bearer abc.def.ghi"
    sanitized = sanitize_style_analysis_error_message(message)

    assert "sk-secret123456" not in sanitized
    assert "abc.def.ghi" not in sanitized
    assert "[REDACTED]" in sanitized


def test_plot_analysis_error_sanitizer_redacts_sensitive_tokens() -> None:
    from app.services.plot_analysis_jobs import sanitize_plot_analysis_error_message

    message = "upstream failed for https://example.com/v1?api_key=sk-secret123456&x=1"
    sanitized = sanitize_plot_analysis_error_message(message)

    assert "sk-secret123456" not in sanitized
    assert "api_key=[REDACTED]" in sanitized
