"""
Tests for the BiConvLSTM layer and its integration as a third optional
forecaster architecture, alongside the ConvLSTM baseline and the per-cell
BiLSTM variant.
"""
import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.bushfire.bilstm import PerCellBiLSTMLayer
from src.models.bushfire.biconvlstm import BiConvLSTMLayer
from src.models.bushfire.ts_convlstm_forecaster import (
    ForecasterConfig,
    MultivariateTSForecaster,
)

MODES = ["convlstm", "convlstm_bilstm", "convlstm_biconvlstm"]


def make_config(mode, input_channels=7, horizon=2, output_channels=7):
    """Build a ForecasterConfig selecting the given architecture mode."""
    if mode == "convlstm":
        return ForecasterConfig(
            input_channels=input_channels, horizon=horizon, output_channels=output_channels,
        )
    if mode == "convlstm_bilstm":
        return ForecasterConfig(
            input_channels=input_channels, horizon=horizon, output_channels=output_channels,
            use_bilstm=True, bilstm_hidden_size=8,
        )
    if mode == "convlstm_biconvlstm":
        return ForecasterConfig(
            input_channels=input_channels, horizon=horizon, output_channels=output_channels,
            use_biconvlstm=True, biconvlstm_hidden_size=8, biconvlstm_kernel_size=3,
        )
    raise ValueError(f"unknown mode {mode}")


def make_model(mode, input_channels=7, horizon=2, output_channels=7):
    return MultivariateTSForecaster(
        make_config(mode, input_channels, horizon, output_channels)
    )


# ---------------------------------------------------------------------------
# Model-level tests, parameterised across all three architectures
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mode", MODES)
def test_output_shape_and_values(mode):
    model = make_model(mode)
    x = torch.rand(1, 10, 4, 4, 7)
    y = model.predict(x)
    assert y.shape == (1, 2, 4, 4, 7)
    assert not torch.isnan(y).any()
    assert not torch.isinf(y).any()
    assert y.min() >= 0.0 and y.max() <= 1.0


@pytest.mark.parametrize("mode", MODES)
def test_grid_size_independence(mode):
    """Flexible, including non-square, spatial grid dimensions."""
    model = make_model(mode)
    y1 = model.predict(torch.rand(1, 10, 4, 4, 7))
    y2 = model.predict(torch.rand(1, 10, 6, 8, 7))
    assert y1.shape == (1, 2, 4, 4, 7)
    assert y2.shape == (1, 2, 6, 8, 7)


@pytest.mark.parametrize("mode", MODES)
def test_deterministic_in_eval_mode(mode):
    model = make_model(mode)
    x = torch.rand(1, 10, 4, 4, 7)
    y1 = model.predict(x)
    y2 = model.predict(x)
    assert torch.equal(y1, y2)


@pytest.mark.parametrize("mode", MODES)
def test_batch_and_sequence_lengths_are_flexible(mode):
    model = make_model(mode)
    y1 = model.predict(torch.rand(1, 3, 4, 4, 7))
    y2 = model.predict(torch.rand(2, 6, 4, 4, 7))
    assert y1.shape == (1, 2, 4, 4, 7)
    assert y2.shape == (2, 2, 4, 4, 7)


@pytest.mark.parametrize("mode", MODES)
def test_input_validation_rejected(mode):
    model = make_model(mode)
    with pytest.raises(ValueError, match="shape"):
        model.predict(torch.rand(1, 10, 4, 4))
    with pytest.raises(ValueError, match="channel"):
        model.predict(torch.rand(1, 10, 4, 4, 3))


@pytest.mark.parametrize("mode", MODES)
def test_gradients_flow_through_full_model(mode):
    model = make_model(mode)
    x = torch.rand(2, 5, 4, 4, 7)

    y_hat = model(x)
    loss = y_hat.sum()
    loss.backward()

    for name, param in model.named_parameters():
        assert param.grad is not None, f"{name} received no gradient"
        assert not torch.isnan(param.grad).any(), f"{name} gradient is NaN"
        assert not torch.isinf(param.grad).any(), f"{name} gradient is infinite"


@pytest.mark.parametrize("mode", MODES)
def test_save_load_roundtrip(mode, tmp_path):
    model = make_model(mode)
    x = torch.rand(1, 10, 4, 4, 7)
    y_before = model.predict(x)

    ckpt = tmp_path / f"checkpoint_{mode}.pth"
    model.save(str(ckpt))
    loaded = MultivariateTSForecaster.load(str(ckpt))
    y_after = loaded.predict(x)

    assert torch.equal(y_before, y_after)
    assert loaded.config.architecture == mode


# ---------------------------------------------------------------------------
# Production-scale functional smoke test (kept out of the default run)
# ---------------------------------------------------------------------------

@pytest.mark.slow
@pytest.mark.parametrize("mode", MODES)
def test_production_scale_inference(mode):
    """Single forward pass at the project's real production dimensions
    (Victoria grid: 143 x 201 cells, 60-step history, 7 input features)."""
    torch.manual_seed(0)
    model = make_model(mode)
    x = torch.rand(1, 60, 143, 201, 7)

    y = model.predict(x)

    assert y.shape == (1, 2, 143, 201, 7)
    assert not torch.isnan(y).any()
    assert not torch.isinf(y).any()
    assert y.min() >= 0.0 and y.max() <= 1.0


# ---------------------------------------------------------------------------
# Config / architecture selection
# ---------------------------------------------------------------------------

def test_baseline_is_default():
    config = ForecasterConfig(input_channels=7)
    assert config.use_bilstm is False
    assert config.use_biconvlstm is False
    assert config.architecture == "convlstm"

    model = MultivariateTSForecaster(config)
    assert model.bilstm is None
    assert model.biconvlstm is None
    assert model.temporal_layer is None


def test_both_flags_raises_at_config_construction():
    with pytest.raises(ValueError):
        ForecasterConfig(input_channels=7, use_bilstm=True, use_biconvlstm=True)


def test_both_flags_raises_at_model_construction_for_pickled_config():
    """__post_init__ doesn't run on a config restored from pickle, so the
    model must re-check the mutual-exclusion invariant itself."""
    config = ForecasterConfig(input_channels=7, use_bilstm=True)
    config.use_biconvlstm = True  # simulate a pickled config bypassing __post_init__
    with pytest.raises(ValueError):
        MultivariateTSForecaster(config)


@pytest.mark.parametrize("mode", MODES)
def test_config_selection_builds_expected_layers(mode):
    model = make_model(mode)
    if mode == "convlstm":
        assert model.bilstm is None
        assert model.biconvlstm is None
    elif mode == "convlstm_bilstm":
        assert isinstance(model.bilstm, PerCellBiLSTMLayer)
        assert model.biconvlstm is None
        assert model.temporal_layer is model.bilstm
    elif mode == "convlstm_biconvlstm":
        assert isinstance(model.biconvlstm, BiConvLSTMLayer)
        assert model.bilstm is None
        assert model.temporal_layer is model.biconvlstm


def test_biconvlstm_projection_channels_match_bilstm():
    """Default biconvlstm_hidden_size=8 gives 2*8=16 channels, matching
    hidden_size_2=16, so the projection head has 16 input channels in every
    mode (mirrors test_bilstm_toggle_changes_architecture_and_channel_flow)."""
    baseline = make_model("convlstm")
    with_bilstm = make_model("convlstm_bilstm")
    with_biconvlstm = make_model("convlstm_biconvlstm")

    assert baseline.projection.in_channels == 16
    assert with_bilstm.projection.in_channels == 16
    assert with_biconvlstm.projection.in_channels == 16


# ---------------------------------------------------------------------------
# Checkpoint compatibility
# ---------------------------------------------------------------------------

def test_checkpoint_missing_new_fields_still_loads(tmp_path):
    """A checkpoint whose config predates use_biconvlstm (etc.) must still load.

    Real unpickling reconstructs an instance via ``object.__new__`` plus a
    restored ``__dict__`` — it never calls ``__init__``/``__post_init__``.
    That is simulated directly here (rather than via ``del`` on a live
    instance) because, for dataclass fields with literal bool/int defaults,
    Python leaves the default as a class-level attribute; deleting the
    *instance* attribute would silently fall back to that class attribute
    and not actually reproduce a pre-fix checkpoint's shape.
    """
    config = ForecasterConfig(input_channels=7, use_bilstm=True, bilstm_hidden_size=8)
    model = MultivariateTSForecaster(config)

    old_config = object.__new__(ForecasterConfig)
    old_config.__dict__.update({
        "input_channels": 7,
        "horizon": 1,
        "output_channels": 1,
        "hidden_size_1": 32,
        "hidden_size_2": 16,
        "dropout": 0.2,
        "use_bilstm": True,
        "bilstm_hidden_size": 8,
        # use_biconvlstm / biconvlstm_hidden_size / biconvlstm_kernel_size
        # intentionally absent from __dict__, as they would be for a
        # checkpoint pickled before this PR.
    })

    ckpt = tmp_path / "old_checkpoint.pth"
    torch.save({"model_state_dict": model.state_dict(), "config": old_config}, ckpt)

    loaded = MultivariateTSForecaster.load(str(ckpt))
    assert loaded.config.architecture == "convlstm_bilstm"
    assert isinstance(loaded.bilstm, PerCellBiLSTMLayer)
    assert loaded.config.use_biconvlstm is False
    assert loaded.config.biconvlstm_hidden_size == 8
    assert loaded.config.biconvlstm_kernel_size == 3

    x = torch.rand(1, 10, 4, 4, 7)
    y = loaded.predict(x)
    assert y.shape == (1, 1, 4, 4, 1)


def test_state_dict_is_namespaced_per_layer():
    bilstm_model = make_model("convlstm_bilstm")
    bilstm_keys = bilstm_model.state_dict().keys()
    assert any(k.startswith("bilstm.") for k in bilstm_keys)
    assert not any(k.startswith("biconvlstm.") for k in bilstm_keys)

    biconvlstm_model = make_model("convlstm_biconvlstm")
    biconvlstm_keys = biconvlstm_model.state_dict().keys()
    assert any(k.startswith("biconvlstm.") for k in biconvlstm_keys)
    assert not any(k.startswith("bilstm.") for k in biconvlstm_keys)


def test_mismatched_architecture_checkpoint_rejected_loudly():
    """A checkpoint from one optional-layer architecture must not partially
    load into a model built with a different one."""
    bilstm_model = make_model("convlstm_bilstm")
    biconvlstm_model = make_model("convlstm_biconvlstm")
    with pytest.raises(RuntimeError):
        biconvlstm_model.load_state_dict(bilstm_model.state_dict())


# ---------------------------------------------------------------------------
# BiConvLSTMLayer unit tests
# ---------------------------------------------------------------------------

def test_biconvlstm_layer_output_shape_and_output_size():
    layer = BiConvLSTMLayer(input_channels=5, hidden_channels=8, kernel_size=3)
    assert layer.output_size == 16

    x = torch.rand(2, 6, 5, 4, 4)
    y = layer(x)
    assert y.shape == (2, 16, 4, 4)


@pytest.mark.parametrize("kernel_size", [2, 4, 0, -1, -3])
def test_biconvlstm_layer_rejects_invalid_kernel_size(kernel_size):
    with pytest.raises(ValueError):
        BiConvLSTMLayer(input_channels=3, hidden_channels=4, kernel_size=kernel_size)


def test_biconvlstm_layer_input_validation():
    layer = BiConvLSTMLayer(input_channels=5, hidden_channels=8, kernel_size=3)
    with pytest.raises(ValueError, match="shape"):
        layer(torch.rand(6, 5, 4, 4))  # wrong ndim
    with pytest.raises(ValueError, match="channel"):
        layer(torch.rand(2, 6, 3, 4, 4))  # wrong channel count
    with pytest.raises(ValueError, match="timestep"):
        layer(torch.rand(2, 0, 5, 4, 4))  # empty sequence


def test_biconvlstm_forward_and_backward_cells_are_distinct():
    layer = BiConvLSTMLayer(input_channels=4, hidden_channels=6, kernel_size=3)
    assert layer.forward_cell is not layer.backward_cell

    fwd_weight = layer.forward_cell.conv.weight
    bwd_weight = layer.backward_cell.conv.weight
    assert not torch.equal(fwd_weight, bwd_weight)


def test_biconvlstm_backward_pass_reads_sequence_in_reverse():
    """With shared weights, the backward half of the output for a sequence
    must equal the forward half of the output for the reversed sequence."""
    torch.manual_seed(0)
    hidden_channels = 4
    layer = BiConvLSTMLayer(input_channels=3, hidden_channels=hidden_channels, kernel_size=3)
    layer.backward_cell.load_state_dict(layer.forward_cell.state_dict())

    x = torch.rand(2, 7, 3, 5, 5)
    x_reversed = x.flip(dims=[1])

    y = layer(x)
    y_reversed_input = layer(x_reversed)

    backward_half = y[:, hidden_channels:]
    forward_half_of_reversed = y_reversed_input[:, :hidden_channels]

    assert torch.allclose(backward_half, forward_half_of_reversed, atol=1e-6)


def test_biconvlstm_propagates_between_neighbouring_cells():
    """BiConvLSTM's convolutional gates mix information across the spatial
    grid; changing a single input pixel must change its neighbours' output.
    This must hold at the layer level, independent of any shared trunk."""
    torch.manual_seed(0)
    layer = BiConvLSTMLayer(input_channels=1, hidden_channels=2, kernel_size=3)
    layer.eval()

    x1 = torch.zeros(1, 1, 1, 5, 5)
    x2 = x1.clone()
    x2[0, 0, 0, 2, 2] = 10.0  # perturb only the centre cell

    with torch.no_grad():
        y1 = layer(x1)
        y2 = layer(x2)

    # An immediate neighbour of the perturbed cell must change.
    assert not torch.allclose(y1[0, :, 1, 2], y2[0, :, 1, 2])
    # A far-away, unconnected cell (kernel_size=3, single timestep) must not.
    assert torch.allclose(y1[0, :, 0, 0], y2[0, :, 0, 0])


def test_percell_bilstm_does_not_propagate_between_cells():
    """The existing per-cell BiLSTM applies shared weights independently to
    each cell, so perturbing one input cell must never affect another."""
    torch.manual_seed(0)
    layer = PerCellBiLSTMLayer(input_size=1, hidden_size=2)
    layer.eval()

    x1 = torch.zeros(1, 1, 1, 5, 5)
    x2 = x1.clone()
    x2[0, 0, 0, 2, 2] = 10.0  # perturb only the centre cell

    with torch.no_grad():
        y1 = layer(x1)
        y2 = layer(x2)

    # No other cell's output may change, including immediate neighbours.
    assert torch.allclose(y1[0, :, 1, 2], y2[0, :, 1, 2])
    assert torch.allclose(y1[0, :, 0, 0], y2[0, :, 0, 0])
    # But the perturbed cell itself must change.
    assert not torch.allclose(y1[0, :, 2, 2], y2[0, :, 2, 2])
