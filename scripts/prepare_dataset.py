from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

from common import ROOT, git_commit, sha256_file

OFFICIAL_URL = "https://github.com/ultralytics/assets/releases/download/v0.0.0/construction-ppe.zip"
UPSTREAM_CLASS_MAP = {
    0: "helmet",
    1: "gloves",
    2: "vest",
    3: "boots",
    4: "goggles",
    5: "none",
    6: "Person",
    7: "no_helmet",
    8: "no_goggle",
    9: "no_gloves",
    10: "no_boots",
}
UPSTREAM_TO_CANONICAL = {6: 0, 0: 1, 7: 2}
CANONICAL_CLASS_MAP = {0: "Person", 1: "Hardhat", 2: "NO-Hardhat"}
DEFAULT_LIMITS = {"train": 180, "val": 60, "test": 60}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        print(f"using existing archive: {destination}")
        return
    print(f"downloading official dataset: {url}")
    with urllib.request.urlopen(url, timeout=120) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def find_source_root(raw_dir: Path) -> Path:
    candidates = [raw_dir / "construction-ppe", raw_dir]
    candidates.extend(path for path in raw_dir.iterdir() if path.is_dir())
    for candidate in candidates:
        if (candidate / "images" / "train").is_dir() and (candidate / "labels" / "train").is_dir():
            return candidate
    raise FileNotFoundError(f"could not find extracted Construction-PPE dataset under {raw_dir}")


def target_classes(label_path: Path) -> set[int]:
    found: set[int] = set()
    if not label_path.exists():
        return found
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        try:
            upstream = int(float(parts[0]))
        except ValueError:
            continue
        if upstream in UPSTREAM_TO_CANONICAL:
            found.add(UPSTREAM_TO_CANONICAL[upstream])
    return found


def deterministic_select(images: list[Path], labels_dir: Path, limit: int | None) -> list[Path]:
    ranked = sorted(images, key=lambda p: hashlib.sha256(p.name.encode()).hexdigest())
    if limit is None or limit <= 0 or len(ranked) <= limit:
        return ranked

    selected: list[Path] = []
    selected_set: set[Path] = set()
    per_class_target = max(1, limit // 6)
    for class_id in CANONICAL_CLASS_MAP:
        count = 0
        for image in ranked:
            label = labels_dir / f"{image.stem}.txt"
            if class_id in target_classes(label) and image not in selected_set:
                selected.append(image)
                selected_set.add(image)
                count += 1
                if count >= per_class_target:
                    break
    for image in ranked:
        if len(selected) >= limit:
            break
        if image not in selected_set:
            selected.append(image)
            selected_set.add(image)
    return sorted(selected[:limit], key=lambda p: p.name)


def remap_label(source: Path, destination: Path, class_counts: Counter[int]) -> int:
    kept = []
    if source.exists():
        for line in source.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            upstream = int(float(parts[0]))
            if upstream not in UPSTREAM_TO_CANONICAL:
                continue
            canonical = UPSTREAM_TO_CANONICAL[upstream]
            kept.append(" ".join([str(canonical), *parts[1:]]))
            class_counts[canonical] += 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return len(kept)


def dataset_fingerprint(processed: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in processed.rglob("*") if p.is_file() and p.name != "manifest.json"):
        digest.update(str(path.relative_to(processed)).encode())
        digest.update(sha256_file(path).encode())
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=ROOT / "data/raw/construction-ppe.zip")
    parser.add_argument("--full", action="store_true", help="process all official images rather than the compact lab subset")
    parser.add_argument("--train-limit", type=int, default=DEFAULT_LIMITS["train"])
    parser.add_argument("--val-limit", type=int, default=DEFAULT_LIMITS["val"])
    parser.add_argument("--test-limit", type=int, default=DEFAULT_LIMITS["test"])
    args = parser.parse_args()

    raw_dir = ROOT / "data/raw"
    processed = ROOT / "data/processed/ppe-v1"
    archive = args.archive.resolve()
    download(OFFICIAL_URL, archive)
    if not zipfile.is_zipfile(archive):
        raise RuntimeError(f"download is not a valid ZIP: {archive}")

    extract_marker = raw_dir / ".construction-ppe-extracted"
    if not extract_marker.exists():
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(raw_dir)
        extract_marker.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")

    source_root = find_source_root(raw_dir)
    if processed.exists():
        shutil.rmtree(processed)
    processed.mkdir(parents=True)

    split_counts: dict[str, dict] = {}
    total_annotations = Counter()
    limits = {"train": args.train_limit, "val": args.val_limit, "test": args.test_limit}
    for split in ("train", "val", "test"):
        src_images_dir = source_root / "images" / split
        src_labels_dir = source_root / "labels" / split
        images = [p for p in src_images_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES]
        selected = deterministic_select(images, src_labels_dir, None if args.full else limits[split])
        annotations = 0
        split_classes = Counter()
        for image in selected:
            out_image = processed / "images" / split / image.name
            out_label = processed / "labels" / split / f"{image.stem}.txt"
            out_image.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image, out_image)
            annotations += remap_label(src_labels_dir / f"{image.stem}.txt", out_label, split_classes)
        total_annotations.update(split_classes)
        split_counts[split] = {
            "upstream_images": len(images),
            "selected_images": len(selected),
            "canonical_annotations": annotations,
            "class_annotations": {CANONICAL_CLASS_MAP[k]: split_classes[k] for k in CANONICAL_CLASS_MAP},
        }

    data_yaml = {
        "path": "data/processed/ppe-v1",
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": CANONICAL_CLASS_MAP,
    }
    (processed / "data.yaml").write_text(yaml.safe_dump(data_yaml, sort_keys=False), encoding="utf-8")
    (ROOT / "data/ppe.yaml").write_text(yaml.safe_dump(data_yaml, sort_keys=False), encoding="utf-8")

    manifest = {
        "dataset_version": "ppe-v1",
        "source_dataset": "Ultralytics Construction-PPE",
        "source_url": OFFICIAL_URL,
        "source_class_map": UPSTREAM_CLASS_MAP,
        "canonical_class_map": CANONICAL_CLASS_MAP,
        "upstream_to_canonical_id_map": UPSTREAM_TO_CANONICAL,
        "selection_mode": "full" if args.full else "deterministic-compact-lab-subset",
        "split_counts": split_counts,
        "total_canonical_annotations": {CANONICAL_CLASS_MAP[k]: total_annotations[k] for k in CANONICAL_CLASS_MAP},
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "preprocessing_script": "scripts/prepare_dataset.py",
        "preprocessing_git_commit": git_commit(),
    }
    manifest["dataset_fingerprint_sha256"] = dataset_fingerprint(processed)
    (processed / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
