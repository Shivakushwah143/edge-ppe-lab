from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import settings
from app.metrics import DETECTIONS_TOTAL, INFERENCE_FAILURES, INFERENCE_LATENCY, INFERENCE_REQUESTS, MODEL_INFO
from app.model_runtime import RuntimeModel
from app.schemas import PredictionResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("edge_ppe")

runtime: RuntimeModel | None = None
startup_error: str | None = None


def _load_runtime() -> RuntimeModel:
    """Resolve the model this process will serve, or explain why it serves none.

    Degraded boot (``EDGE_PPE_STARTUP_STRICT=false``) is documented as: serve
    ``/health`` straight away and report ``/ready`` 503 because no model is loaded.
    That contract cannot be honoured while startup blocks on a remote registry, and
    MLflow's default HTTP retry policy is patient enough to stall a boot for minutes
    against an unreachable tracking server (measured: ~247s for one alias lookup).
    So when strict mode is off and no explicit local artifact was requested, skip
    remote resolution instead of waiting on network retries. Strict mode, which is
    what every deployment path here uses, is unchanged.
    """
    if not settings.startup_strict and not settings.model_path:
        raise RuntimeError(
            "degraded boot: EDGE_PPE_STARTUP_STRICT=false and EDGE_PPE_MODEL_PATH is unset, "
            "so remote registry resolution was skipped; serving /health and reporting 503 on /ready"
        )
    return RuntimeModel.from_settings(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global runtime, startup_error
    try:
        runtime = _load_runtime()
        identity = runtime.identity
        provider = ",".join(identity.providers)
        MODEL_INFO.labels(
            identity.registered_model,
            identity.version,
            identity.alias,
            identity.format,
            identity.sha256,
            provider,
        ).set(1)
        logger.info(
            "model_loaded name=%s version=%s alias=%s sha256=%s provider=%s",
            identity.registered_model,
            identity.version,
            identity.alias,
            identity.sha256,
            provider,
        )
    except Exception as exc:
        startup_error = f"{type(exc).__name__}: {exc}"
        logger.exception("model_startup_failed")
        if settings.startup_strict:
            raise
    yield


app = FastAPI(title="EdgePPE Lab", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "alive"}


@app.get("/ready")
def ready() -> dict:
    if runtime is None:
        raise HTTPException(status_code=503, detail={"ready": False, "error": startup_error})
    return {"ready": True, "model_version": runtime.identity.version}


@app.get("/model-info")
def model_info() -> dict:
    if runtime is None:
        raise HTTPException(status_code=503, detail={"ready": False, "error": startup_error})
    identity = runtime.identity
    return {
        "registered_model": identity.registered_model,
        "concrete_model_version": identity.version,
        "registry_alias_used": identity.alias,
        "format": identity.format,
        "sha256": identity.sha256,
        "execution_provider": list(identity.providers),
        "loaded_timestamp": identity.loaded_at,
        "source_run_id": identity.source_run_id,
        "input_contract": identity.input_contract,
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(image: UploadFile = File(...)) -> PredictionResponse:
    if runtime is None:
        raise HTTPException(status_code=503, detail="model is not ready")
    INFERENCE_REQUESTS.inc()
    started = time.perf_counter()
    try:
        payload = await image.read()
        decoded, detections = runtime.detector.predict_bytes(payload)
        for detection in detections:
            DETECTIONS_TOTAL.labels(detection["class_name"]).inc()
        return PredictionResponse(
            model_version=runtime.identity.version,
            image_width=int(decoded.shape[1]),
            image_height=int(decoded.shape[0]),
            detections=detections,
        )
    except ValueError as exc:
        INFERENCE_FAILURES.inc()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        INFERENCE_FAILURES.inc()
        logger.exception("inference_failed")
        raise HTTPException(status_code=500, detail=f"inference failed: {type(exc).__name__}") from exc
    finally:
        INFERENCE_LATENCY.observe(time.perf_counter() - started)


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
