from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class Detection(BaseModel):
    class_id: int
    class_name: Literal["Person", "Hardhat", "NO-Hardhat"]
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BoundingBox


class PredictionResponse(BaseModel):
    model_version: str
    image_width: int
    image_height: int
    detections: list[Detection]
