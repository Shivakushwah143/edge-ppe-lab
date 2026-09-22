from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from common import MODEL_NAME, ROOT, load_release, save_release

# Allow `python scripts/validate_parity.py` to import the app package from the project root.
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.model_runtime import OnnxDetector
from app.postprocessing import box_iou


def pt_detections(result) -> list[dict]:
    detections = []
    if result.boxes is None:
        return detections
    for box in result.boxes:
        xyxy = box.xyxy[0].cpu().numpy().tolist()
        class_id = int(box.cls[0].item())
        detections.append({
            "class_id": class_id,
            "class_name": result.names[class_id],
            "confidence": float(box.conf[0].item()),
            "bbox": {"x1": xyxy[0], "y1": xyxy[1], "x2": xyxy[2], "y2": xyxy[3]},
        })
    return detections


def match(pt: list[dict], ort: list[dict]) -> dict:
    unmatched_ort = set(range(len(ort)))
    matched = []
    unmatched_pt = []
    for left in pt:
        best_idx = None
        best_iou = -1.0
        a = list(left["bbox"].values())
        for idx in list(unmatched_ort):
            right = ort[idx]
            if right["class_id"] != left["class_id"]:
                continue
            score = box_iou(a, list(right["bbox"].values()))
            if score > best_iou:
                best_iou, best_idx = score, idx
        if best_idx is None:
            unmatched_pt.append(left)
            continue
        right = ort[best_idx]
        unmatched_ort.remove(best_idx)
        matched.append({
            "class_id": left["class_id"],
            "iou": best_iou,
            "confidence_delta": abs(left["confidence"] - right["confidence"]),
        })
    return {"matched": matched, "unmatched_pt": unmatched_pt, "unmatched_onnx": [ort[i] for i in sorted(unmatched_ort)]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True)
    parser.add_argument("--images", type=int, default=5)
    parser.add_argument("--min-iou", type=float, default=0.95)
    parser.add_argument("--max-confidence-delta", type=float, default=0.03)
    parser.add_argument("--max-unmatched-fraction", type=float, default=0.10)
    args = parser.parse_args()
    metadata = load_release(args.release)
    if not metadata.get("onnx_path"):
        raise RuntimeError("export ONNX before parity validation")

    from ultralytics import YOLO
    import mlflow

    checkpoint = (ROOT / metadata["checkpoint_path"]).resolve()
    onnx_path = (ROOT / metadata["onnx_path"]).resolve()
    pt_model = YOLO(str(checkpoint))
    detector = OnnxDetector(onnx_path, confidence=0.25, iou_threshold=0.45)
    images = sorted((ROOT / "data/processed/ppe-v1/images/val").glob("*"))[: args.images]
    if not images:
        raise RuntimeError("no validation images found")

    rows = []
    total_predictions = 0
    total_unmatched = 0
    all_iou = []
    all_conf_delta = []
    for image in images:
        pt = pt_detections(pt_model.predict(str(image), imgsz=detector.input_height, conf=0.25, iou=0.45, device="cpu", verbose=False)[0])
        import cv2
        arr = cv2.imread(str(image))
        ort = detector.predict_bgr(arr)
        comparison = match(pt, ort)
        unmatched = len(comparison["unmatched_pt"]) + len(comparison["unmatched_onnx"])
        total_predictions += max(len(pt), len(ort), 1)
        total_unmatched += unmatched
        all_iou.extend(item["iou"] for item in comparison["matched"])
        all_conf_delta.extend(item["confidence_delta"] for item in comparison["matched"])
        rows.append({"image": str(image.relative_to(ROOT)), "pytorch": pt, "onnxruntime": ort, **comparison})

    min_iou = min(all_iou) if all_iou else (1.0 if total_unmatched == 0 else 0.0)
    max_conf_delta = max(all_conf_delta) if all_conf_delta else 0.0
    unmatched_fraction = total_unmatched / total_predictions
    passed = min_iou >= args.min_iou and max_conf_delta <= args.max_confidence_delta and unmatched_fraction <= args.max_unmatched_fraction
    report = {
        "release": args.release,
        "passed": passed,
        "tolerance": {
            "min_iou": args.min_iou,
            "max_confidence_delta": args.max_confidence_delta,
            "max_unmatched_fraction": args.max_unmatched_fraction,
        },
        "summary": {
            "images": len(images),
            "minimum_matched_iou": min_iou,
            "maximum_confidence_delta": max_conf_delta,
            "unmatched_fraction": unmatched_fraction,
            "onnx_execution_providers": detector.providers,
        },
        "comparisons": rows,
    }
    report_path = ROOT / "var/releases" / args.release / "parity_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", metadata["tracking_uri"])
    mlflow.set_tracking_uri(tracking_uri)
    with mlflow.start_run(run_id=metadata["run_id"]):
        mlflow.log_artifact(str(report_path), artifact_path=f"deployment/{args.release}")
        mlflow.log_metric("parity_min_iou", min_iou)
        mlflow.log_metric("parity_max_confidence_delta", max_conf_delta)
        mlflow.log_metric("parity_unmatched_fraction", unmatched_fraction)
    client = mlflow.MlflowClient(tracking_uri=tracking_uri)
    version = str(metadata["registered_model_version"])
    client.set_model_version_tag(MODEL_NAME, version, "parity_status", "passed" if passed else "failed")
    metadata["parity_status"] = "passed" if passed else "failed"
    metadata["parity_report_path"] = str(report_path.relative_to(ROOT))
    save_release(args.release, metadata)
    print(json.dumps(report["summary"] | {"passed": passed}, indent=2))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
