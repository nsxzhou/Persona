from __future__ import annotations

from app.services.checkpointer_factory import ConfiguredCheckpointerFactory


class NovelWorkflowCheckpointerFactory(ConfiguredCheckpointerFactory):
    checkpoint_url_settings_name = "novel_workflow_checkpoint_url"


__all__ = ["NovelWorkflowCheckpointerFactory"]
