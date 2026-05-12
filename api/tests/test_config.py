from __future__ import annotations


def test_plot_analysis_max_attempts_defaults_to_style_attempts_env(monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    monkeypatch.setenv("PERSONA_STYLE_ANALYSIS_MAX_ATTEMPTS", "5")
    monkeypatch.delenv("PERSONA_PLOT_ANALYSIS_MAX_ATTEMPTS", raising=False)
    get_settings.cache_clear()

    try:
        settings = get_settings()
        assert settings.style_analysis_max_attempts == 5
        assert settings.plot_analysis_max_attempts == 5
    finally:
        get_settings.cache_clear()


def test_plot_analysis_max_attempts_has_plot_specific_override(monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    monkeypatch.setenv("PERSONA_STYLE_ANALYSIS_MAX_ATTEMPTS", "5")
    monkeypatch.setenv("PERSONA_PLOT_ANALYSIS_MAX_ATTEMPTS", "7")
    get_settings.cache_clear()

    try:
        settings = get_settings()
        assert settings.style_analysis_max_attempts == 5
        assert settings.plot_analysis_max_attempts == 7
    finally:
        get_settings.cache_clear()
