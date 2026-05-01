from __future__ import annotations

from app.services.base_analysis_storage import BaseAnalysisStorageService


class StyleAnalysisStorageService(BaseAnalysisStorageService):
    @property
    def sample_dir_name(self) -> str:
        return "style-samples"

    @property
    def artifact_dir_name(self) -> str:
        return "style-analysis-artifacts"
