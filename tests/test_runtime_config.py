import pytest

from app.config import Settings
from app.model_runtime import RuntimeModel


def test_explicit_model_path_requires_concrete_version():
    settings = Settings(model_path="/tmp/model.onnx", model_version=None)
    with pytest.raises(RuntimeError, match="EDGE_PPE_MODEL_VERSION"):
        RuntimeModel.from_settings(settings)
