from __future__ import annotations

import logging

from app.services.base_analysis_storage import BaseAnalysisStorageService

logger = logging.getLogger(__name__)


class StyleAnalysisStorageService(BaseAnalysisStorageService):
    @property
    def sample_dir_name(self) -> str:
        return "style-samples"

    @property
    def artifact_dir_name(self) -> str:
        return "style-analysis-artifacts"
