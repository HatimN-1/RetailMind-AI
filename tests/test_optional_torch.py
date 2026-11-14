import numpy as np
import pytest


def test_autoencoder_is_valid_architecture(tmp_path, monkeypatch):
    pytest.importorskip('torch')
    # Unit-scale tensor exercise, independent of the full packaged evaluation.
    x = np.random.default_rng(42).normal(size=(40, 7)).astype('float32')
    y = np.array([0]*18+[1]*2, dtype=int)
    from retailmind import train
    monkeypatch.setattr(train, 'MODELS', tmp_path)
    result = train.train_autoencoder(x, x[:20], y, epochs=1)
    assert result['epochs'] == 1
    assert (tmp_path / 'autoencoder.pt').exists()
