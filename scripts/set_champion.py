from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

from common import MODEL_NAME, RELEASES, ROOT, load_release, require_qualified

CHAMPION = "champion"
# Status carried by every parity-qualified version that is not the current champion.
DEMOTED_STATUS = "qualified"


def find_release_by_version(version: str) -> tuple[str, dict]:
    for path in sorted(RELEASES.glob("v*/release.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if str(data.get("registered_model_version")) == str(version):
            return path.parent.name, data
    raise RuntimeError(f"no local release metadata maps to registered model version {version}")


def resolve_target(release: str | None, version: str | None) -> tuple[str, dict, str]:
    if bool(release) == bool(version):
        raise RuntimeError("provide exactly one of --release or --version")
    if release:
        metadata = load_release(release)
        concrete = metadata.get("registered_model_version")
        if not concrete:
            raise RuntimeError(f"{release} has not been registered yet")
        return release, metadata, str(concrete)
    assert version is not None
    matched_release, metadata = find_release_by_version(version)
    return matched_release, metadata, str(version)


def _alias_version(client) -> str | None:
    """Current champion alias target, or None when the alias does not exist yet."""
    try:
        return str(client.get_model_version_by_alias(MODEL_NAME, CHAMPION).version)
    except Exception:
        return None


def _demote_other_champions(client, version: str) -> list[str]:
    """Re-tag every other version that still claims release_status=champion.

    MLflow stages are deprecated, so this uses aliases plus version tags only. A version
    can only have been promoted after passing the parity gate, so the demoted status is
    `qualified`.
    """
    demoted: list[str] = []
    for candidate in client.search_model_versions(f"name='{MODEL_NAME}'"):
        if str(candidate.version) == str(version):
            continue
        if (candidate.tags or {}).get("release_status") == CHAMPION:
            client.set_model_version_tag(MODEL_NAME, candidate.version, "release_status", DEMOTED_STATUS)
            demoted.append(str(candidate.version))
    return sorted(demoted)


def main() -> None:
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--release", help="local release name such as v1 or v2")
    target.add_argument("--version", help="concrete MLflow model version")
    args = parser.parse_args()

    release, metadata, version = resolve_target(args.release, args.version)
    require_qualified(metadata, release)

    import mlflow

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", metadata["tracking_uri"])
    client = mlflow.MlflowClient(tracking_uri=tracking_uri)
    registered = client.get_model_version(MODEL_NAME, version)
    if registered.run_id != metadata.get("run_id"):
        raise RuntimeError(
            f"registry/local lineage mismatch for {MODEL_NAME} v{version}: "
            f"registry run={registered.run_id}, local run={metadata.get('run_id')}"
        )

    # The mutable alias is the authoritative deployment pointer; release_status is
    # informational metadata that must never contradict it. Clear the champion status
    # from every other version before promoting, so exactly one version claims it.
    previous_version = _alias_version(client)
    demoted = _demote_other_champions(client, version)

    client.set_registered_model_alias(MODEL_NAME, CHAMPION, version)
    client.set_model_version_tag(MODEL_NAME, version, "release_status", CHAMPION)
    deployment = {
        "registered_model": MODEL_NAME,
        "alias": CHAMPION,
        "concrete_version": version,
        "release": release,
        "previous_version": previous_version,
        "demoted_versions": demoted,
        "changed_at": datetime.now(timezone.utc).isoformat(),
    }
    path = ROOT / "var/deployment/champion.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(deployment, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(deployment, indent=2))


if __name__ == "__main__":
    main()
