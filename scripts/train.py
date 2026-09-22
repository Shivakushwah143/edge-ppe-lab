from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import yaml
from datetime import datetime, timezone
from pathlib import Path

from common import ROOT, git_commit, project_relative, read_yaml, release_dir, save_release
from verify_dataset import verify


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    cfg = read_yaml(args.config.resolve())
    release = cfg["release"]
    output_dir = release_dir(release)
    dataset_path = (ROOT / cfg["data"]).resolve()
    verification = verify(dataset_path)
    # Ultralytics may resolve relative dataset roots through its global datasets directory.
    # Write an execution-only YAML with an absolute project-local root to keep this lab deterministic.
    dataset_cfg = read_yaml(dataset_path)
    dataset_root = Path(dataset_cfg["path"])
    if not dataset_root.is_absolute():
        dataset_root = (ROOT / dataset_root).resolve()
    dataset_cfg["path"] = str(dataset_root)
    runtime_dataset_path = ROOT / "var" / f"dataset-{release}.yaml"
    runtime_dataset_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_dataset_path.write_text(yaml.safe_dump(dataset_cfg, sort_keys=False), encoding="utf-8")

    import mlflow
    from ultralytics import YOLO, settings as yolo_settings

    yolo_settings.update({"mlflow": False})
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("edge-ppe-lab")

    train_root = ROOT / "var/training"
    train_root.mkdir(parents=True, exist_ok=True)
    params = {
        "base_model": cfg["model"],
        "epochs": int(cfg["epochs"]),
        "imgsz": int(cfg["imgsz"]),
        "batch": int(cfg["batch"]),
        "device": cfg.get("device", "cpu"),
        "workers": int(cfg.get("workers", 2)),
        "seed": int(cfg.get("seed", 42)),
        "fraction": float(cfg.get("fraction", 1.0)),
        "lr0": float(cfg.get("lr0", 0.01)),
        "dataset_version": "ppe-v1",
        "git_commit": git_commit(),
        "release": release,
    }

    with mlflow.start_run(run_name=f"edge-ppe-{release}") as run:
        mlflow.log_params(params)
        mlflow.set_tags({
            "edge_ppe.release": release,
            "edge_ppe.dataset_version": "ppe-v1",
            "edge_ppe.git_commit": params["git_commit"],
        })
        model = YOLO(cfg["model"])
        results = model.train(
            data=str(runtime_dataset_path),
            epochs=params["epochs"],
            imgsz=params["imgsz"],
            batch=params["batch"],
            device=params["device"],
            workers=params["workers"],
            seed=params["seed"],
            fraction=params["fraction"],
            lr0=params["lr0"],
            project=str(train_root),
            name=release,
            exist_ok=True,
            verbose=True,
        )
        metrics = {str(k): float(v) for k, v in getattr(results, "results_dict", {}).items() if _numeric(v)}
        for key, value in metrics.items():
            # MLflow metric names reject characters such as parentheses: metrics/precision(B) -> metrics_precision_B
            metric_name = re.sub(r"[^0-9A-Za-z_\-. :/]", "_", key.replace("/", "_"))
            mlflow.log_metric(metric_name, value)

        save_dir = Path(results.save_dir)
        best = save_dir / "weights/best.pt"
        if not best.is_file():
            raise RuntimeError(f"training completed without best.pt: {best}")
        checkpoint = output_dir / "best.pt"
        shutil.copy2(best, checkpoint)
        mlflow.log_artifact(str(checkpoint), artifact_path="checkpoints")
        manifest = ROOT / "data/processed/ppe-v1/manifest.json"
        mlflow.log_artifact(str(manifest), artifact_path="dataset")
        run_id = run.info.run_id

    metadata = {
        "release": release,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "tracking_uri": tracking_uri,
        "dataset_version": "ppe-v1",
        "dataset_verification": verification,
        "git_commit": params["git_commit"],
        "training_config": params,
        "checkpoint_path": project_relative(checkpoint),
        "checkpoint_artifact_path": "checkpoints/best.pt",
        "metrics": metrics,
        "registered_model_name": os.getenv("EDGE_PPE_MODEL_NAME", "edge-ppe-detector"),
        "registered_model_version": None,
        "onnx_path": None,
        "onnx_sha256": None,
        "parity_status": "not-run",
    }
    save_release(release, metadata)
    print(json.dumps(metadata, indent=2))


def _numeric(value) -> bool:
    try:
        float(value)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    main()
