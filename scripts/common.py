from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "var" / "releases"
MODEL_NAME = os.getenv("EDGE_PPE_MODEL_NAME", "edge-ppe-detector")


def release_dir(release: str) -> Path:
    if not release.startswith("v") or not release[1:].isdigit():
        raise ValueError("release must look like v1 or v2")
    path = RELEASES / release
    path.mkdir(parents=True, exist_ok=True)
    return path


def release_metadata_path(release: str) -> Path:
    return release_dir(release) / "release.json"


def load_release(release: str) -> dict[str, Any]:
    path = release_metadata_path(release)
    if not path.exists():
        raise FileNotFoundError(f"release metadata not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_release(release: str, data: dict[str, Any]) -> None:
    path = release_metadata_path(release)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "UNKNOWN"


def read_yaml(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def project_relative(path: str | Path) -> str:
    p = Path(path).resolve()
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def absolute_project_path(value: str | Path) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (ROOT / p).resolve()


def require_qualified(metadata: dict[str, Any], release: str) -> None:
    """Reject deployment promotion unless ONNX parity qualification is complete."""
    if metadata.get("parity_status") != "passed":
        raise RuntimeError(
            f"refusing to promote {release}: parity_status={metadata.get('parity_status')!r}; "
            "run PT↔ONNX parity validation first"
        )
    if not metadata.get("onnx_path") or not metadata.get("onnx_sha256"):
        raise RuntimeError(f"refusing to promote {release}: qualified ONNX metadata is incomplete")
