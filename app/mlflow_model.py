from __future__ import annotations

import pandas as pd


class PPECheckpointPyFunc:
    """Factory for a real MLflow pyfunc wrapper around an Ultralytics checkpoint.

    Kept separate from deployment inference: the registry object captures checkpoint lineage,
    while the production runtime uses a parity-qualified ONNX artifact attached to the same run/version.
    """

    @staticmethod
    def build():
        import mlflow.pyfunc

        class _Model(mlflow.pyfunc.PythonModel):
            def load_context(self, context):
                from ultralytics import YOLO

                self.model = YOLO(context.artifacts["checkpoint"])

            def predict(self, context, model_input, params=None):
                if not isinstance(model_input, pd.DataFrame) or "image_path" not in model_input.columns:
                    raise ValueError("model_input must be a DataFrame with an image_path column")
                rows = []
                for path in model_input["image_path"].tolist():
                    result = self.model.predict(path, verbose=False)[0]
                    rows.append({"image_path": path, "detections": int(len(result.boxes))})
                return pd.DataFrame(rows)

        return _Model()
