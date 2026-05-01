from __future__ import annotations

from app.services.checkpointer_factory import ConfiguredCheckpointerFactory


class StyleAnalysisCheckpointerFactory(ConfiguredCheckpointerFactory):
    """Long-lived singleton factory — ``get()`` memoises the checkpointer
    and its async context manager. Only one instance should be kept alive
    per process; call ``aclose()`` during shutdown.
    """

    checkpoint_url_settings_name = "style_analysis_checkpoint_url"
    delete_thread_failure_message = "Failed to delete checkpointer thread for job_id=%s: %s"


__all__ = ["StyleAnalysisCheckpointerFactory"]
