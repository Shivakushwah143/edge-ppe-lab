from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class LetterboxMeta:
    scale: float
    pad_x: float
    pad_y: float
    original_height: int
    original_width: int
    input_height: int
    input_width: int


def letterbox(image: np.ndarray, target_height: int, target_width: int) -> tuple[np.ndarray, LetterboxMeta]:
    if image is None or image.size == 0:
        raise ValueError("image is empty")
    height, width = image.shape[:2]
    scale = min(target_width / width, target_height / height)
    resized_width = int(round(width * scale))
    resized_height = int(round(height * scale))

    resized = cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR)
    pad_w = target_width - resized_width
    pad_h = target_height - resized_height
    left = int(round(pad_w / 2 - 0.1))
    right = int(round(pad_w / 2 + 0.1))
    top = int(round(pad_h / 2 - 0.1))
    bottom = int(round(pad_h / 2 + 0.1))
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))

    rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
    tensor = np.ascontiguousarray(rgb.transpose(2, 0, 1), dtype=np.float32) / 255.0
    tensor = np.expand_dims(tensor, axis=0)

    return tensor, LetterboxMeta(
        scale=scale,
        pad_x=float(left),
        pad_y=float(top),
        original_height=height,
        original_width=width,
        input_height=target_height,
        input_width=target_width,
    )
