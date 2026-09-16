from __future__ import annotations

import json
import os

from common import MODEL_NAME, RELEASES


def main() -> None:
    local = []
    for path in sorted(RELEASES.glob("v*/release.json")):
        local.append(json.loads(path.read_text(encoding="utf-8")))
    output = {"local_releases": local}
    try:
        import mlflow
        client = mlflow.MlflowClient(tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
        champion = client.get_model_version_by_alias(MODEL_NAME, "champion")
        output["registry_champion"] = {"version": champion.version, "run_id": champion.run_id, "tags": champion.tags}
    except Exception as exc:
        output["registry_error"] = f"{type(exc).__name__}: {exc}"
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
