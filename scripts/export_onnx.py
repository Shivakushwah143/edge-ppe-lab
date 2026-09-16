from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from common import MODEL_NAME, ROOT, load_release, project_relative, save_release, sha256_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True)
    parser.add_argument("--opset", type=int, default=17)
    args = parser.parse_args()
    metadata = load_release(args.release)
    checkpoint = (ROOT / metadata["checkpoint_path"]).resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    if not metadata.get("registered_model_version"):
        raise RuntimeError("register the model before exporting ONNX")

    import mlflow
    import onnx
    import onnxruntime as ort
    from ultralytics import YOLO

    imgsz = int(metadata["training_config"]["imgsz"])
    model = YOLO(str(checkpoint))
    exported = Path(
        model.export(
            format="onnx",
            imgsz=imgsz,
            opset=args.opset,
            simplify=False,
            dynamic=False,
            half=False,
            nms=False,
            device="cpu",
        )
    ).resolve()
    destination = (ROOT / "var/releases" / args.release / "model.onnx").resolve()
    if exported != destination:
        shutil.copy2(exported, destination)
    digest = sha256_file(destination)
    onnx_model = onnx.load(str(destination))
    opsets = {entry.domain or "ai.onnx": entry.version for entry in onnx_model.opset_import}
    session = ort.InferenceSession(str(destination), providers=["CPUExecutionProvider"])
    input_info = session.get_inputs()[0]
    contract = {
        "input": {"name": input_info.name, "shape": input_info.shape, "dtype": input_info.type},
        "outputs": [{"name": out.name, "shape": out.shape, "dtype": out.type} for out in session.get_outputs()],
        "providers": session.get_providers(),
        "opsets": opsets,
        "preprocessing": "BGR decode -> aspect-preserving letterbox(fill=114) -> RGB -> NCHW float32 /255",
        "postprocessing": "decode Ultralytics detection output -> class confidence filter -> class-wise NMS -> undo letterbox",
    }

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", metadata["tracking_uri"])
    mlflow.set_tracking_uri(tracking_uri)
    artifact_path = f"deployment/{args.release}/model.onnx"
    with mlflow.start_run(run_id=metadata["run_id"]):
        mlflow.log_artifact(str(destination), artifact_path=f"deployment/{args.release}")
        contract_path = destination.parent / "onnx_contract.json"
        contract_path.write_text(json.dumps(contract, indent=2, default=str) + "\n", encoding="utf-8")
        mlflow.log_artifact(str(contract_path), artifact_path=f"deployment/{args.release}")

    client = mlflow.MlflowClient(tracking_uri=tracking_uri)
    version = str(metadata["registered_model_version"])
    client.set_model_version_tag(MODEL_NAME, version, "onnx_artifact_path", artifact_path)
    client.set_model_version_tag(MODEL_NAME, version, "onnx_sha256", digest)
    client.set_model_version_tag(MODEL_NAME, version, "parity_status", "not-run")

    metadata.update({
        "onnx_path": project_relative(destination),
        "onnx_sha256": digest,
        "onnx_artifact_path": artifact_path,
        "onnx_contract": contract,
        "export_opset": args.opset,
        "parity_status": "not-run",
    })
    save_release(args.release, metadata)
    print(json.dumps({"onnx": str(destination), "sha256": digest, "contract": contract}, indent=2, default=str))


if __name__ == "__main__":
    main()
