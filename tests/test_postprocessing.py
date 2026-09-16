import numpy as np

from app.postprocessing import box_iou, decode_yolo_output
from app.preprocessing import LetterboxMeta


def test_iou_identical():
    assert box_iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0


def test_decode_raw_yolo_output():
    # [1, 4+3, 2] -> xywh + class scores, with one strong Person candidate.
    output = np.zeros((1, 7, 2), dtype=np.float32)
    output[0, 0:4, 0] = [160, 160, 100, 100]
    output[0, 4:, 0] = [0.9, 0.05, 0.01]
    meta = LetterboxMeta(1.0, 0.0, 0.0, 320, 320, 320, 320)
    detections = decode_yolo_output(output, meta, 0.25, 0.45)
    assert len(detections) == 1
    assert detections[0]["class_name"] == "Person"
    assert detections[0]["bbox"]["x1"] == 110.0


def test_decode_raw_yolo_output_anchor_major():
    # Same raw contract but already shaped [anchors, 4+nc].
    output = np.zeros((1, 2, 7), dtype=np.float32)
    output[0, 0, 0:4] = [160, 160, 80, 80]
    output[0, 0, 4:] = [0.05, 0.85, 0.01]
    meta = LetterboxMeta(1.0, 0.0, 0.0, 320, 320, 320, 320)
    detections = decode_yolo_output(output, meta, 0.25, 0.45)
    assert len(detections) == 1
    assert detections[0]["class_name"] == "Hardhat"


def test_decode_end_to_end_output():
    output = np.array([[[10, 20, 100, 120, 0.8, 2], [0, 0, 1, 1, 0.1, 0]]], dtype=np.float32)
    meta = LetterboxMeta(1.0, 0.0, 0.0, 320, 320, 320, 320)
    detections = decode_yolo_output(output, meta, 0.25, 0.45)
    assert len(detections) == 1
    assert detections[0]["class_name"] == "NO-Hardhat"
