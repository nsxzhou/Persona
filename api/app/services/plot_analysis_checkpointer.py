from __future__ import annotations

from app.services.style_analysis_checkpointer import (
    StyleAnalysisCheckpointerFactory,
    normalize_checkpoint_url,
)


class PlotAnalysisCheckpointerFactory(StyleAnalysisCheckpointerFactory):
    pass


__all__ = ["PlotAnalysisCheckpointerFactory", "normalize_checkpoint_url"]
