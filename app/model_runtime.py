from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.config import Settings
from app.postprocessing import CANONICAL_NAMES, decode_yolo_output
from app.preprocessing import letterbox

logger = logging.getLogger(__name__)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class ModelIdentity:
    registered_model: str
    version: str
    alias: str
    format: str
    sha256: str
    source_run_id: str | None
    artifact_path: str
    providers: tuple[str, ...]
    loaded_at: str
    input_contract: dict[str, Any]


class OnnxDetector:
    def __init__(self, model_path: str | Path, confidence: float = 0.25, iou_threshold: float = 0.45):
        self.path = Path(model_path).resolve()
        if not self.path.is_file():
            raise FileNotFoundError(f"ONNX model not found: {self.path}")
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("onnxruntime is required for inference; install project requirements") from exc
        self.confidence = confidence
        self.iou_threshold = iou_threshold
        self.session = ort.InferenceSession(str(self.path), providers=["CPUExecutionProvider"])
        self.input = self.session.get_inputs()[0]
        self.outputs = self.session.get_outputs()
        shape = self.input.shape
        if len(shape) != 4:
            raise RuntimeError(f"expected rank-4 model input, got {shape}")
        self.input_height = _static_dim(shape[2], "height")
        self.input_width = _static_dim(shape[3], "width")

    @property
    def providers(self) -> tuple[str, ...]:
        return tuple(self.session.get_providers())

    @property
    def input_contract(self) -> dict[str, Any]:
        return {
            "name": self.input.name,
            "shape": [str(v) if not isinstance(v, int) else v for v in self.input.shape],
            "dtype": self.input.type,
            "layout": "NCHW",
            "normalization": "RGB float32 / 255.0",
            "resize": "aspect-preserving letterbox, fill=114",
            "outputs": [{"name": out.name, "shape": [str(v) for v in out.shape], "dtype": out.type} for out in self.outputs],
        }

    def predict_bgr(self, image: np.ndarray) -> list[dict]:
        tensor, meta = letterbox(image, self.input_height, self.input_width)
        output_values = self.session.run(None, {self.input.name: tensor})
        if not output_values:
            raise RuntimeError("ONNX model returned no outputs")
        return decode_yolo_output(
            output_values[0],
            meta,
            confidence_threshold=self.confidence,
            iou_threshold=self.iou_threshold,
            class_names=CANONICAL_NAMES,
        )

    def predict_bytes(self, payload: bytes) -> tuple[np.ndarray, list[dict]]:
        image = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("uploaded file is not a decodable image")
        return image, self.predict_bgr(image)


class RuntimeModel:
    def __init__(self, detector: OnnxDetector, identity: ModelIdentity):
        self.detector = detector
        self.identity = identity

    @classmethod
    def from_settings(cls, settings: Settings) -> "RuntimeModel":
        if settings.model_path:
            if not settings.model_version:
                raise RuntimeError("EDGE_PPE_MODEL_VERSION is required when EDGE_PPE_MODEL_PATH is used")
            path = Path(settings.model_path).resolve()
            detector = OnnxDetector(path, settings.confidence, settings.iou_threshold)
            identity = _identity(
                settings.model_name,
                settings.model_version,
                "local-explicit",
                path,
                detector,
                source_run_id=None,
            )
            return cls(detector, identity)

        try:
            import mlflow
            from mlflow import MlflowClient
        except ImportError as exc:
            raise RuntimeError("MLflow is required to resolve the champion model alias") from exc

        mlflow.set_tracking_uri(settings.tracking_uri)
        client = MlflowClient(tracking_uri=settings.tracking_uri)
        model_version = client.get_model_version_by_alias(settings.model_name, settings.model_alias)
        concrete_version = str(model_version.version)
        run_id = model_version.run_id
        if not run_id:
            raise RuntimeError(f"registered model version {concrete_version} has no source run")
        artifact_path = model_version.tags.get("onnx_artifact_path")
        expected_sha = model_version.tags.get("onnx_sha256")
        parity = model_version.tags.get("parity_status")
        if not artifact_path:
            raise RuntimeError(f"model version {concrete_version} has no onnx_artifact_path tag")
        if parity != "passed":
            raise RuntimeError(f"model version {concrete_version} is not parity-qualified (status={parity!r})")

        cache_dir = Path(settings.model_cache_dir).resolve() / f"v{concrete_version}"
        cache_dir.mkdir(parents=True, exist_ok=True)
        downloaded = Path(client.download_artifacts(run_id, artifact_path, str(cache_dir))).resolve()
        actual_sha = sha256_file(downloaded)
        if expected_sha and actual_sha != expected_sha:
            raise RuntimeError(
                f"downloaded model SHA256 mismatch: expected {expected_sha}, got {actual_sha}"
            )
        detector = OnnxDetector(downloaded, settings.confidence, settings.iou_threshold)
        identity = _identity(
            settings.model_name,
            concrete_version,
            settings.model_alias,
            downloaded,
            detector,
            source_run_id=run_id,
        )
        return cls(detector, identity)


def _identity(
    model_name: str,
    version: str,
    alias: str,
    path: Path,
    detector: OnnxDetector,
    source_run_id: str | None,
) -> ModelIdentity:
    return ModelIdentity(
        registered_model=model_name,
        version=version,
        alias=alias,
        format="onnx",
        sha256=sha256_file(path),
        source_run_id=source_run_id,
        artifact_path=str(path),
        providers=detector.providers,
        loaded_at=datetime.now(timezone.utc).isoformat(),
        input_contract=detector.input_contract,
    )


def _static_dim(value: Any, label: str) -> int:
    if isinstance(value, int) and value > 0:
        return value
    raise RuntimeError(f"EdgePPE Lab requires static ONNX input {label}; got {value!r}")
