from __future__ import annotations

import importlib
import json
import platform
import shutil
import subprocess
import sys

MODULES = ["torch", "ultralytics", "mlflow", "onnx", "onnxruntime", "fastapi", "uvicorn", "prometheus_client", "cv2"]


def main() -> None:
    modules = {}
    for name in MODULES:
        try:
            module = importlib.import_module(name)
            modules[name] = {"available": True, "version": getattr(module, "__version__", "unknown")}
        except Exception as exc:
            modules[name] = {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    commands = {}
    for name in ["git", "docker", "systemctl", "ss", "curl"]:
        path = shutil.which(name)
        commands[name] = {"path": path, "available": bool(path)}
    if commands["systemctl"]["available"]:
        proc = subprocess.run(["systemctl", "is-system-running"], text=True, capture_output=True)
        commands["systemctl"]["state"] = (proc.stdout or proc.stderr).strip()
    print(json.dumps({"python": sys.version, "platform": platform.platform(), "modules": modules, "commands": commands}, indent=2))


if __name__ == "__main__":
    main()
