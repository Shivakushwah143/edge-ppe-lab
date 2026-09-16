from __future__ import annotations

from collections import defaultdict

import cv2
import numpy as np

from app.preprocessing import LetterboxMeta


CANONICAL_NAMES = ("Person", "Hardhat", "NO-Hardhat")


def box_iou(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    ax1, ay1, ax2, ay2 = map(float, a)
    bx1, by1, bx2, by2 = map(float, b)
    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, inter_x2 - inter_x1), max(0.0, inter_y2 - inter_y1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _undo_letterbox_xyxy(box: np.ndarray, meta: LetterboxMeta) -> np.ndarray:
    x1, y1, x2, y2 = box.astype(float)
    x1 = (x1 - meta.pad_x) / meta.scale
    x2 = (x2 - meta.pad_x) / meta.scale
    y1 = (y1 - meta.pad_y) / meta.scale
    y2 = (y2 - meta.pad_y) / meta.scale
    x1 = float(np.clip(x1, 0, meta.original_width))
    x2 = float(np.clip(x2, 0, meta.original_width))
    y1 = float(np.clip(y1, 0, meta.original_height))
    y2 = float(np.clip(y2, 0, meta.original_height))
    return np.array([x1, y1, x2, y2], dtype=np.float32)


def _xywh_to_xyxy(boxes: np.ndarray) -> np.ndarray:
    result = boxes.copy().astype(np.float32)
    result[:, 0] = boxes[:, 0] - boxes[:, 2] / 2
    result[:, 1] = boxes[:, 1] - boxes[:, 3] / 2
    result[:, 2] = boxes[:, 0] + boxes[:, 2] / 2
    result[:, 3] = boxes[:, 1] + boxes[:, 3] / 2
    return result


def decode_yolo_output(
    output: np.ndarray,
    meta: LetterboxMeta,
    confidence_threshold: float,
    iou_threshold: float,
    class_names: tuple[str, ...] = CANONICAL_NAMES,
) -> list[dict]:
    """Decode a standard Ultralytics detection ONNX output.

    Supports raw YOLO outputs shaped [1, 4+nc, anchors] or [1, anchors, 4+nc],
    plus end-to-end outputs shaped [1, detections, 6] as xyxy/conf/class.
    """
    pred = np.asarray(output)
    if pred.ndim == 3 and pred.shape[0] == 1:
        pred = pred[0]
    if pred.ndim != 2:
        raise ValueError(f"unsupported ONNX detection output shape: {tuple(np.asarray(output).shape)}")

    # End-to-end/NMS-integrated export: x1,y1,x2,y2,confidence,class_id.
    if pred.shape[1] == 6:
        rows = pred[pred[:, 4] >= confidence_threshold]
        detections: list[dict] = []
        for row in rows:
            class_id = int(round(float(row[5])))
            if 0 <= class_id < len(class_names):
                box = _undo_letterbox_xyxy(row[:4], meta)
                detections.append(_record(class_id, class_names[class_id], float(row[4]), box))
        return detections

    expected_no_objectness = 4 + len(class_names)
    expected_with_objectness = 5 + len(class_names)
    if pred.shape[0] in {expected_no_objectness, expected_with_objectness} and pred.shape[1] not in {expected_no_objectness, expected_with_objectness}:
        pred = pred.T
    if pred.shape[1] not in {expected_no_objectness, expected_with_objectness}:
        raise ValueError(
            f"expected {expected_no_objectness} or {expected_with_objectness} values per candidate, got {pred.shape[1]}"
        )

    boxes = _xywh_to_xyxy(pred[:, :4])
    if pred.shape[1] == expected_no_objectness:
        class_scores = pred[:, 4:]
    else:
        objectness = pred[:, 4:5]
        class_scores = pred[:, 5:] * objectness

    class_ids = np.argmax(class_scores, axis=1)
    confidences = class_scores[np.arange(class_scores.shape[0]), class_ids]
    keep_mask = confidences >= confidence_threshold
    boxes = boxes[keep_mask]
    class_ids = class_ids[keep_mask]
    confidences = confidences[keep_mask]

    candidates_by_class: dict[int, list[int]] = defaultdict(list)
    for index, class_id in enumerate(class_ids.tolist()):
        candidates_by_class[int(class_id)].append(index)

    kept: list[int] = []
    for class_id, indexes in candidates_by_class.items():
        cls_boxes = boxes[indexes]
        xywh = np.column_stack(
            [cls_boxes[:, 0], cls_boxes[:, 1], cls_boxes[:, 2] - cls_boxes[:, 0], cls_boxes[:, 3] - cls_boxes[:, 1]]
        ).tolist()
        cls_scores = confidences[indexes].astype(float).tolist()
        selected = cv2.dnn.NMSBoxes(xywh, cls_scores, confidence_threshold, iou_threshold)
        if len(selected):
            for local_index in np.asarray(selected).reshape(-1).tolist():
                kept.append(indexes[int(local_index)])

    kept.sort(key=lambda idx: float(confidences[idx]), reverse=True)
    detections = []
    for idx in kept:
        class_id = int(class_ids[idx])
        if not 0 <= class_id < len(class_names):
            continue
        box = _undo_letterbox_xyxy(boxes[idx], meta)
        detections.append(_record(class_id, class_names[class_id], float(confidences[idx]), box))
    return detections


def _record(class_id: int, class_name: str, confidence: float, box: np.ndarray) -> dict:
    return {
        "class_id": class_id,
        "class_name": class_name,
        "confidence": round(float(confidence), 6),
        "bbox": {
            "x1": round(float(box[0]), 3),
            "y1": round(float(box[1]), 3),
            "x2": round(float(box[2]), 3),
            "y2": round(float(box[3]), 3),
        },
    }
