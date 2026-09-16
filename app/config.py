from __future__ import annotations

import os
from dataclasses import dataclass, field


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    model_name: str = field(default_factory=lambda: os.getenv("EDGE_PPE_MODEL_NAME", "edge-ppe-detector"))
    model_alias: str = field(default_factory=lambda: os.getenv("EDGE_PPE_MODEL_ALIAS", "champion"))
    tracking_uri: str = field(default_factory=lambda: os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
    model_path: str | None = field(default_factory=lambda: os.getenv("EDGE_PPE_MODEL_PATH"))
    model_version: str | None = field(default_factory=lambda: os.getenv("EDGE_PPE_MODEL_VERSION"))
    confidence: float = field(default_factory=lambda: float(os.getenv("EDGE_PPE_CONFIDENCE", "0.25")))
    iou_threshold: float = field(default_factory=lambda: float(os.getenv("EDGE_PPE_IOU_THRESHOLD", "0.45")))
    model_cache_dir: str = field(default_factory=lambda: os.getenv("EDGE_PPE_MODEL_CACHE", "var/model-cache"))
    startup_strict: bool = field(default_factory=lambda: _bool_env("EDGE_PPE_STARTUP_STRICT", True))


settings = Settings()
