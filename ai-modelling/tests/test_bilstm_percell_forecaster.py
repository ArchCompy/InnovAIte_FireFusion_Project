"""
Tests for the optional per-cell BiLSTM in the main ConvLSTM forecaster.
"""
import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.bushfire.bilstm import PerCellBiLSTMLayer
from src.models.bushfire.ts_convlstm_forecaster import (
    ForecasterConfig,
    MultivariateTSForecaster,
)


def make_model(input_channels=7, horizon=2, output_channels=7):
    config = ForecasterConfig(
        input_channels=input_channels,
        horizon=horizon,
        output_channels=output_channels,
        use_bilstm=True,
        bilstm_hidden_size=8,
    )
    return MultivariateTSForecaster(config)


def test_output_shape_and_values():
    model = make_model()
    x = torch.rand(1, 10, 4, 4, 7)
    y = model.predict(x)
    assert y.shape == (1, 2, 4, 4, 7)
    assert not torch.isnan(y).any()
    assert y.min() >= 0.0 and y.max() <= 1.0


def test_grid_size_independence():
    model = make_model()
    y1 = model.predict(torch.rand(1, 10, 4, 4, 7))
    y2 = model.predict(torch.rand(1, 10, 6, 8, 7))
    assert y1.shape == (1, 2, 4, 4, 7)
    assert y2.shape == (1, 2, 6, 8, 7)


def test_deterministic_in_eval_mode():
    model = make_model()
    x = torch.rand(1, 10, 4, 4, 7)
    y1 = model.predict(x)
    y2 = model.predict(x)
    assert torch.equal(y1, y2)


def test_save_load_roundtrip(tmp_path):
    model = make_model()
    x = torch.rand(1, 10, 4, 4, 7)
    y_before = model.predict(x)

    ckpt = tmp_path / "checkpoint.pth"
    model.save(str(ckpt))
    loaded = MultivariateTSForecaster.load(str(ckpt))
    y_after = loaded.predict(x)

    assert torch.equal(y_before, y_after)


def test_baseline_mode_remains_available():
    config = ForecasterConfig(
        input_channels=7,
        horizon=2,
        output_channels=7,
        use_bilstm=False,
    )
    model = MultivariateTSForecaster(config)
    y = model.predict(torch.rand(1, 10, 4, 4, 7))

    assert y.shape == (1, 2, 4, 4, 7)


def test_batch_and_sequence_lengths_are_flexible():
    model = make_model()
    y1 = model.predict(torch.rand(1, 3, 4, 4, 7))
    y2 = model.predict(torch.rand(2, 6, 4, 4, 7))

    assert y1.shape == (1, 2, 4, 4, 7)
    assert y2.shape == (2, 2, 4, 4, 7)


def test_bilstm_toggle_changes_architecture_and_channel_flow():
    """The toggle selects the expected architecture and 32 -> 16 -> 16 -> 1 flow."""
    baseline = MultivariateTSForecaster(
        ForecasterConfig(input_channels=7, use_bilstm=False)
    )
    with_bilstm = MultivariateTSForecaster(
        ForecasterConfig(input_channels=7, use_bilstm=True, bilstm_hidden_size=8)
    )

    assert baseline.bilstm is None
    assert isinstance(with_bilstm.bilstm, PerCellBiLSTMLayer)
    assert with_bilstm.convlstm1.hidden_channels == 32
    assert with_bilstm.convlstm2.hidden_channels == 16
    assert with_bilstm.bilstm.output_size == 16
    assert baseline.projection.in_channels == with_bilstm.projection.in_channels == 16
    assert with_bilstm.projection.out_channels == 1


@pytest.mark.parametrize("use_bilstm", [False, True])
def test_gradients_flow_through_full_model(use_bilstm):
    """A backward pass must populate gradients for every parameter, in both
    modes, otherwise the model cannot actually be trained."""
    config = ForecasterConfig(
        input_channels=7, use_bilstm=use_bilstm, bilstm_hidden_size=8
    )
    model = MultivariateTSForecaster(config)
    x = torch.rand(2, 5, 4, 4, 7)

    y_hat = model(x)
    loss = y_hat.sum()
    loss.backward()

    for name, param in model.named_parameters():
        assert param.grad is not None, f"{name} received no gradient"
        assert not torch.isnan(param.grad).any(), f"{name} gradient is NaN"


def test_model_and_layer_input_validation():
    """Both public model components reject incompatible tensor contracts."""
    model = make_model()
    with pytest.raises(ValueError, match="shape"):
        model.predict(torch.rand(1, 10, 4, 4))
    with pytest.raises(ValueError, match="channel"):
        model.predict(torch.rand(1, 10, 4, 4, 3))

    layer = PerCellBiLSTMLayer(input_size=16, hidden_size=8)
    with pytest.raises(ValueError, match="shape"):
        layer(torch.rand(1, 10, 16, 4, 4).squeeze(0))  # wrong ndim
    with pytest.raises(ValueError, match="channel"):
        layer(torch.rand(1, 10, 5, 4, 4))  # wrong channel count


@pytest.mark.parametrize("use_bilstm", [False, True])
def test_production_scale_inference(use_bilstm):
    """Run a single forward pass at the project's real production dimensions
    (Victoria grid: 143 x 201 cells, 60-step daily/12-hourly history, 7
    input features), the same shape used in PR #212's manual functional
    validation. Confirms the model doesn't just work on tiny toy tensors."""
    torch.manual_seed(0)
    config = ForecasterConfig(
        input_channels=7,
        horizon=2,
        output_channels=7,
        use_bilstm=use_bilstm,
        bilstm_hidden_size=8,
    )
    model = MultivariateTSForecaster(config)
    x = torch.rand(1, 60, 143, 201, 7)

    y = model.predict(x)

    assert y.shape == (1, 2, 143, 201, 7)
    assert not torch.isnan(y).any()
    assert not torch.isinf(y).any()
    assert y.min() >= 0.0 and y.max() <= 1.0
