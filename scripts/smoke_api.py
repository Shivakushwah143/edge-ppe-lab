from __future__ import annotations

import argparse
import json

import requests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    for path in ("/health", "/ready", "/model-info"):
        response = requests.get(args.base_url + path, timeout=10)
        print(path, response.status_code, response.text)
        response.raise_for_status()
    with open(args.image, "rb") as handle:
        response = requests.post(args.base_url + "/predict", files={"image": handle}, timeout=60)
    print("/predict", response.status_code, json.dumps(response.json(), indent=2))
    response.raise_for_status()
    response = requests.get(args.base_url + "/metrics", timeout=10)
    response.raise_for_status()
    print("/metrics contains inference_requests_total:", "inference_requests_total" in response.text)


if __name__ == "__main__":
    main()
