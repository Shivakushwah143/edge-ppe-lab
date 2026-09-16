from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import yaml

from common import ROOT

EXPECTED = {0: "Person", 1: "Hardhat", 2: "NO-Hardhat"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def verify(config_path: Path) -> dict:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    names = {int(k): v for k, v in cfg["names"].items()}
    if names != EXPECTED:
        raise ValueError(f"class map mismatch: expected {EXPECTED}, got {names}")
    root = Path(cfg["path"])
    if not root.is_absolute():
        root = (ROOT / root).resolve()
    result = {"config": str(config_path), "root": str(root), "splits": {}, "classes": Counter()}
    for split in ("train", "val", "test"):
        images_dir = root / cfg[split]
        labels_dir = root / "labels" / split
        images = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
        if not images:
            raise ValueError(f"no images found for {split}: {images_dir}")
        annotations = 0
        missing_labels = []
        for image in images:
            label = labels_dir / f"{image.stem}.txt"
            if not label.exists():
                missing_labels.append(image.name)
                continue
            for line_number, line in enumerate(label.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) != 5:
                    raise ValueError(f"{label}:{line_number}: expected 5 YOLO fields")
                class_id = int(parts[0])
                coords = [float(v) for v in parts[1:]]
                if class_id not in EXPECTED:
                    raise ValueError(f"{label}:{line_number}: invalid class {class_id}")
                if any(value < 0.0 or value > 1.0 for value in coords):
                    raise ValueError(f"{label}:{line_number}: bbox coordinate outside [0,1]")
                result["classes"][EXPECTED[class_id]] += 1
                annotations += 1
        result["splits"][split] = {
            "images": len(images),
            "annotations": annotations,
            "missing_label_files": missing_labels,
        }
    if any(result["classes"][name] == 0 for name in EXPECTED.values()):
        raise ValueError(f"one or more canonical classes has zero annotations: {dict(result['classes'])}")
    result["classes"] = dict(result["classes"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "data/ppe.yaml")
    args = parser.parse_args()
    print(json.dumps(verify(args.config.resolve()), indent=2))


if __name__ == "__main__":
    main()
