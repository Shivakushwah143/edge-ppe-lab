.PHONY: verify dataset mlflow train-v1 register-v1 export-v1 parity-v1 champion-v1 api test
verify:
	python scripts/verify_components.py

dataset:
	python scripts/prepare_dataset.py
	python scripts/verify_dataset.py --config data/ppe.yaml

mlflow:
	./scripts/start_mlflow.sh

train-v1:
	python scripts/train.py --config configs/train-v1.yaml

register-v1:
	python scripts/register_model.py --release v1

export-v1:
	python scripts/export_onnx.py --release v1

parity-v1:
	python scripts/validate_parity.py --release v1

champion-v1:
	python scripts/set_champion.py --release v1

api:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

test:
	python -m pytest -q
