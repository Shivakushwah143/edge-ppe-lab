#!/usr/bin/env python
"""Release contract gate.

Validates the release metadata that is *committed* to the repository (rather than
a re-trained model), so CI can enforce real contracts without the dataset, without
retraining, and without the multi-hundred-megabyte ONNX binaries that are
deliberately not tracked by git.

What this proves, and why each check matters:

1. Registry metadata integrity - each release records a registered model version,
   a concrete ONNX SHA-256 and a parity verdict. If someone edits a number by hand
   or a release is re-exported without re-running parity, the two files disagree
   and this gate fails.
2. ONNX I/O contract - the input/output names, shapes, dtypes, opset and execution
   provider are pinned. `app/postprocessing.py` hard-codes the (1, 4 + n_classes, N)
   layout and `app/preprocessing.py` hard-codes the 320x320 letterbox; if an export
   changed either, the service would silently mis-decode. This catches that.
3. Parity evidence - the recorded PT<->ONNX comparison must actually satisfy the
   tolerance it claims, with no unmatched detections on either side.
4. CPU-only runtime contract - the shipping image and runtime requirements must not
   contain torch/CUDA. The lab has no GPU, so a CUDA dependency creeping into the
   runtime set is a regression, not an optimisation.
5. API surface - the routes the deployment depends on still exist.

Run locally:  python scripts/verify_release_contract.py
Exit code 0 = all contracts hold, 1 = at least one violation.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

RELEASES = ("v1", "v2")

CANONICAL_CLASSES = {0: "Person", 1: "Hardhat", 2: "NO-Hardhat"}
EXPECTED_INPUT = {"name": "images", "shape": [1, 3, 320, 320], "dtype": "tensor(float)"}
EXPECTED_OUTPUT_NAME = "output0"
EXPECTED_OPSET = 17
EXPECTED_PROVIDERS = ["CPUExecutionProvider"]
EXPECTED_IMAGE_SIZE = 320
REGISTERED_MODEL = "edge-ppe-detector"
EXPECTED_ROUTES = {"/health", "/ready", "/model-info", "/predict", "/metrics"}

REQUIRED_RELEASE_KEYS = (
    "release",
    "registered_model_name",
    "registered_model_version",
    "onnx_sha256",
    "onnx_contract",
    "parity_status",
    "parity_report_path",
    "export_opset",
)

HEX64 = re.compile(r"^[0-9a-f]{64}$")

failures: list[str] = []
checks_run = 0


def strip_comments(text: str) -> str:
    """Drop whole-line comments so prose about torch/CUDA is not read as a dependency.

    requirements-runtime.txt explains why torch and the nvidia wheels are absent,
    and docker/Dockerfile states that no CUDA runtime is installed. Scanning the
    raw text would flag those explanations as violations.
    """
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def check(condition: bool, label: str, detail: str = "") -> None:
    global checks_run
    checks_run += 1
    if condition:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}" + (f" :: {detail}" if detail else ""))
        failures.append(label + (f" :: {detail}" if detail else ""))


def load_json(path: Path, label: str) -> dict | None:
    if not path.is_file():
        check(False, label, f"missing file {path.relative_to(REPO)}")
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        check(False, label, f"invalid JSON in {path.relative_to(REPO)}: {exc}")
        return None


def verify_release(release: str) -> None:
    print(f"\n[{release}] release metadata")
    base = REPO / "var" / "releases" / release
    release_json = load_json(base / "release.json", f"{release} release.json parses")
    contract_json = load_json(base / "onnx_contract.json", f"{release} onnx_contract.json parses")
    parity_json = load_json(base / "parity_report.json", f"{release} parity_report.json parses")
    if not (release_json and contract_json and parity_json):
        return

    missing = [k for k in REQUIRED_RELEASE_KEYS if k not in release_json]
    check(not missing, f"{release} release.json has all required keys", f"missing {missing}")

    check(
        release_json.get("registered_model_name") == REGISTERED_MODEL,
        f"{release} registered model name is {REGISTERED_MODEL}",
        f"got {release_json.get('registered_model_name')!r}",
    )
    version = str(release_json.get("registered_model_version", ""))
    check(version.isdigit(), f"{release} records a concrete registry version", f"got {version!r}")

    digest = str(release_json.get("onnx_sha256", ""))
    check(HEX64.match(digest) is not None, f"{release} onnx_sha256 is a sha256 hex digest", digest)

    check(
        release_json.get("parity_status") == "passed",
        f"{release} parity_status is passed",
        f"got {release_json.get('parity_status')!r}",
    )

    # The embedded contract and the standalone contract file must be the same
    # document: release.json is what the deployment reads, and a hand edit to one
    # of them would otherwise go unnoticed.
    check(
        release_json.get("onnx_contract") == contract_json,
        f"{release} embedded onnx_contract matches onnx_contract.json",
    )

    print(f"\n[{release}] ONNX I/O contract")
    check(contract_json.get("input") == EXPECTED_INPUT, f"{release} input contract {EXPECTED_INPUT['shape']}")
    check(
        contract_json.get("opsets", {}).get("ai.onnx") == EXPECTED_OPSET
        and release_json.get("export_opset") == EXPECTED_OPSET,
        f"{release} opset is {EXPECTED_OPSET} in both files",
        f"contract={contract_json.get('opsets')} release={release_json.get('export_opset')}",
    )
    check(
        contract_json.get("providers") == EXPECTED_PROVIDERS,
        f"{release} declares only {EXPECTED_PROVIDERS[0]}",
        f"got {contract_json.get('providers')}",
    )

    outputs = contract_json.get("outputs") or []
    check(len(outputs) == 1, f"{release} has exactly one output tensor", f"got {len(outputs)}")
    if len(outputs) == 1:
        out = outputs[0]
        expected_rows = 4 + len(CANONICAL_CLASSES)
        check(out.get("name") == EXPECTED_OUTPUT_NAME, f"{release} output name is {EXPECTED_OUTPUT_NAME}")
        check(
            out.get("shape", [None])[0] == 1 and out.get("shape", [None, None])[1] == expected_rows,
            f"{release} output rows == 4 bbox + {len(CANONICAL_CLASSES)} classes",
            f"got shape {out.get('shape')}",
        )
        check(
            out.get("dtype") == "tensor(float)",
            f"{release} output dtype is float32",
            f"got {out.get('dtype')!r}",
        )

    print(f"\n[{release}] parity evidence")
    tol = parity_json.get("tolerance") or {}
    summary = parity_json.get("summary") or {}
    comparisons = parity_json.get("comparisons") or []

    check(parity_json.get("passed") is True, f"{release} parity report passed is true")
    check(bool(comparisons), f"{release} parity report has comparisons")
    check(
        summary.get("images") == len(comparisons),
        f"{release} summary.image count matches comparison rows",
        f"{summary.get('images')} vs {len(comparisons)}",
    )

    min_iou = summary.get("minimum_matched_iou")
    max_delta = summary.get("maximum_confidence_delta")
    unmatched_fraction = summary.get("unmatched_fraction")
    check(
        min_iou is not None and min_iou >= tol.get("min_iou", 1.0),
        f"{release} min matched IoU >= {tol.get('min_iou')}",
        f"got {min_iou}",
    )
    check(
        max_delta is not None and max_delta <= tol.get("max_confidence_delta", 0.0),
        f"{release} max confidence delta <= {tol.get('max_confidence_delta')}",
        f"got {max_delta}",
    )
    check(
        unmatched_fraction is not None and unmatched_fraction <= tol.get("max_unmatched_fraction", 0.0),
        f"{release} unmatched fraction <= {tol.get('max_unmatched_fraction')}",
        f"got {unmatched_fraction}",
    )
    check(
        summary.get("onnx_execution_providers") == EXPECTED_PROVIDERS,
        f"{release} parity ran on {EXPECTED_PROVIDERS[0]}",
        f"got {summary.get('onnx_execution_providers')}",
    )

    for comparison in comparisons:
        image = comparison.get("image", "<unnamed>")
        pt = comparison.get("pytorch") or []
        ort = comparison.get("onnxruntime") or []
        matched = comparison.get("matched") or []
        check(
            len(pt) == len(ort) == len(matched)
            and not comparison.get("unmatched_pt")
            and not comparison.get("unmatched_onnx"),
            f"{release} {Path(image).name} has no unmatched detections",
            f"pt={len(pt)} onnx={len(ort)} matched={len(matched)}",
        )


def verify_dataset_contract() -> None:
    print("\n[dataset] canonical class contract")
    try:
        import yaml
    except ModuleNotFoundError:
        check(False, "PyYAML available for the dataset contract check")
        return
    config_path = REPO / "data" / "ppe.yaml"
    if not config_path.is_file():
        check(False, "data/ppe.yaml exists")
        return
    cfg = yaml.safe_load(config_path.read_text())
    names = {int(k): v for k, v in (cfg.get("names") or {}).items()}
    check(names == CANONICAL_CLASSES, "dataset class names are Person / Hardhat / NO-Hardhat", f"got {names}")
    check(
        len(names) + 4 == 4 + len(CANONICAL_CLASSES),
        f"dataset defines {len(CANONICAL_CLASSES)} classes (4 bbox + {len(CANONICAL_CLASSES)} rows per anchor)",
        f"got {len(names)}",
    )


def verify_cpu_only_runtime() -> None:
    print("\n[runtime] CPU-only image contract")
    runtime_reqs = strip_comments((REPO / "requirements-runtime.txt").read_text()).lower()
    forbidden = ("torch", "ultralytics", "nvidia", "cuda", "tensorrt", "onnxruntime-gpu")
    offenders = [name for name in forbidden if name in runtime_reqs]
    check(not offenders, "runtime requirements contain no torch/CUDA/GPU packages", f"found {offenders}")

    dockerfile = (REPO / "docker" / "Dockerfile").read_text()
    lowered = strip_comments(dockerfile).lower()
    check(
        re.search(r"^FROM\s+python:3\.\d+-slim", dockerfile, re.MULTILINE) is not None,
        "Dockerfile builds from a python slim base image",
    )
    check(
        "nvidia" not in lowered and "cuda" not in lowered,
        "Dockerfile installs no CUDA/NVIDIA runtime",
    )
    check("HEALTHCHECK" in dockerfile and "/ready" in dockerfile, "Dockerfile healthcheck probes /ready")
    check(re.search(r"^EXPOSE\s+8000", dockerfile, re.MULTILINE) is not None, "Dockerfile exposes port 8000")
    check(
        re.search(r"^USER\s+(?!root)\S+", dockerfile, re.MULTILINE) is not None,
        "Dockerfile drops to a non-root user",
    )


def verify_api_surface() -> None:
    print("\n[api] service contract")
    try:
        from app.main import app
    except Exception as exc:  # pragma: no cover - reported as a contract failure
        check(False, "app.main imports with the runtime dependency set", f"{type(exc).__name__}: {exc}")
        return

    routes = {route.path for route in app.routes}
    missing = EXPECTED_ROUTES - routes
    check(not missing, "API exposes health/ready/model-info/predict/metrics", f"missing {sorted(missing)}")

    schemas = getattr(app, "openapi", lambda: {})().get("components", {}).get("schemas", {})
    check(
        "PredictionResponse" in schemas,
        "response schema for /predict is declared",
        f"schemas={sorted(schemas)[:6]}",
    )


def main() -> int:
    print("EdgePPE release contract gate")
    print(f"repository root: {REPO}")

    for release in RELEASES:
        verify_release(release)

    print("\n[registry] release distinctness")
    versions = {}
    for release in RELEASES:
        path = REPO / "var" / "releases" / release / "release.json"
        if path.is_file():
            versions[release] = str(json.loads(path.read_text()).get("registered_model_version"))
    check(
        len(set(versions.values())) == len(versions),
        "releases map to distinct registry versions",
        f"got {versions}",
    )

    verify_dataset_contract()
    verify_cpu_only_runtime()
    verify_api_surface()

    print("\n" + "=" * 62)
    if failures:
        print(f"CONTRACT GATE FAILED: {len(failures)} of {checks_run} checks failed")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"CONTRACT GATE PASSED: {checks_run} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
