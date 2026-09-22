from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from common import MODEL_NAME, ROOT, load_release, save_release

# Allow `python scripts/register_model.py` to import the app package from the project root.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True)
    args = parser.parse_args()
    metadata = load_release(args.release)
    checkpoint = (ROOT / metadata["checkpoint_path"]).resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)

    import mlflow
    from app.mlflow_model import PPECheckpointPyFunc

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", metadata.get("tracking_uri", "http://127.0.0.1:5000"))
    mlflow.set_tracking_uri(tracking_uri)
    with mlflow.start_run(run_id=metadata["run_id"]):
        info = mlflow.pyfunc.log_model(
            name="registry_model",
            python_model=PPECheckpointPyFunc.build(),
            artifacts={"checkpoint": str(checkpoint)},
            pip_requirements=["ultralytics==8.4.153", "torch>=2.2,<3", "pandas>=2,<3"],
        )
    model_uri = info.model_uri
    version = mlflow.register_model(model_uri=model_uri, name=MODEL_NAME, await_registration_for=120)
    client = mlflow.MlflowClient(tracking_uri=tracking_uri)
    client.set_model_version_tag(MODEL_NAME, version.version, "release", args.release)
    client.set_model_version_tag(MODEL_NAME, version.version, "dataset_version", metadata["dataset_version"])
    client.set_model_version_tag(MODEL_NAME, version.version, "checkpoint_artifact_path", metadata["checkpoint_artifact_path"])
    client.set_model_version_tag(MODEL_NAME, version.version, "parity_status", "not-run")

    metadata["registered_model_name"] = MODEL_NAME
    metadata["registered_model_version"] = str(version.version)
    metadata["registry_model_uri"] = model_uri
    save_release(args.release, metadata)
    print(json.dumps({"registered_model": MODEL_NAME, "version": str(version.version), "run_id": metadata["run_id"]}, indent=2))


if __name__ == "__main__":
    main()
