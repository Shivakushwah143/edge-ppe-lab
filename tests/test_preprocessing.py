import numpy as np

from app.preprocessing import letterbox


def test_letterbox_contract():
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    tensor, meta = letterbox(image, 320, 320)
    assert tensor.shape == (1, 3, 320, 320)
    assert tensor.dtype == np.float32
    assert meta.scale == 1.6
    assert meta.pad_y == 80.0
