"""
2D ConvLSTM-based Spatiotemporal Forecaster

Defines a 2D ConvLSTM architecture that uses environmental variables to
forecast the probability that each grid cell is burning at the next timestep. Supports configurable input channels, hidden sizes, and dropout, with a
single output channel for the 'is burning' probability.

Architecture:
    - Layer 1: ConvLSTM2d (input_channels -> hidden_size_1)
    - Dropout2d
    - Layer 2: ConvLSTM2d (hidden_size_1 -> hidden_size_2)
    - Dropout2d
    - Optional temporal refinement layer: shared per-cell BiLSTM, or BiConvLSTM
    - Conv2d Projection (temporal features -> horizon * output_channels)
    - Reshape to [batch, horizon, height, width, output_channels]
"""
from dataclasses import dataclass
from typing import Optional, Tuple
import torch
from torch import Tensor, nn
from torch.utils.checkpoint import checkpoint

from .attention import PatchwiseAttention2d
from .bilstm import PerCellBiLSTMLayer
from .biconvlstm import BiConvLSTMLayer
from .convlstm import ConvLSTMCell

__all__ = [
    "ForecasterConfig",
    "ConvLSTMCell",
    "MultivariateTSForecaster",
]

@dataclass
class ForecasterConfig:
    """
    Configuration dataclass for the 2D ConvLSTM spatiotemporal forecaster.

    Attributes:
        input_channels (int): Number of input features per grid cell.
        horizon (int): Number of future timesteps to forecast.
        output_channels (int): Number of output features. Defaults to 1 for the 'is burning' output.
        hidden_size_1 (int): Hidden dimension of first ConvLSTM2d layer.
        hidden_size_2 (int): Hidden dimension of second ConvLSTM2d layer.
        dropout (float): Dropout probability applied after each ConvLSTM2d layer.
        attention (str): Gate operator. "none" uses a standard Conv2d gate; "patchwise" replaces it with patchwise self-attention.
        footprint (int): Patch side length for patchwise attention. Must be odd.
        dilation (int): Spacing between sampled cells in the attention patch.
        share_planes (int): Output channels sharing one attention weight set.
        attention_layers (Tuple[int, ...]): Which ConvLSTM layers (1 and/or 2) use attention when ``attention`` is not "none".
        use_bilstm (bool): Whether to apply the shared per-cell BiLSTM layer.
        bilstm_hidden_size (int): Hidden dimension per BiLSTM direction.
        use_biconvlstm (bool): Whether to apply the BiConvLSTM layer.
        biconvlstm_hidden_size (int): Hidden dimension per BiConvLSTM direction.
        biconvlstm_kernel_size (int): Convolution kernel size used by the BiConvLSTM cells.
    """
    input_channels: int
    horizon: int = 1
    output_channels: int = 1
    hidden_size_1: int = 32
    hidden_size_2: int = 16
    dropout: float = 0.2
    attention: str = "patchwise"
    footprint: int = 7
    dilation: int = 1
    share_planes: int = 8
    attention_layers: Tuple[int, ...] = (1,)
    use_bilstm: bool = False
    bilstm_hidden_size: int = 8
    use_biconvlstm: bool = False
    biconvlstm_hidden_size: int = 8
    biconvlstm_kernel_size: int = 3
    grad_checkpointing: bool = True

    def __post_init__(self) -> None:
        if self.use_bilstm and self.use_biconvlstm:
            raise ValueError(
                "use_bilstm and use_biconvlstm cannot both be True; "
                "at most one optional temporal layer may be active."
            )

    @property
    def architecture(self) -> str:
        """Name of the selected architecture: the single source of truth for model selection."""
        if self.use_bilstm:
            return "convlstm_bilstm"
        if self.use_biconvlstm:
            return "convlstm_biconvlstm"
        return "convlstm"


def _backfill_config_defaults(config: ForecasterConfig) -> ForecasterConfig:
    """Backfill optional fields missing from checkpoints pickled before they existed.

    A checkpoint saved before ``use_biconvlstm`` (or similar) was added
    unpickles without that attribute, and ``__post_init__`` does not run on
    unpickle, so accessing it would raise ``AttributeError``.
    """
    defaults = {
        "use_bilstm": False,
        "bilstm_hidden_size": 8,
        "use_biconvlstm": False,
        "biconvlstm_hidden_size": 8,
        "biconvlstm_kernel_size": 3,
        "grad_checkpointing": True,
    }
    for field_name, default_value in defaults.items():
        if not hasattr(config, field_name):
            setattr(config, field_name, default_value)
    return config


class MultivariateTSForecaster(nn.Module):
    """
    2D ConvLSTM spatiotemporal forecasting model.
    
    Learns patterns from gridded historical sequences to predict the probability
    that each grid cell is burning at the next timestep. Uses two stacked
    ConvLSTM2d layers and can optionally apply a shared BiLSTM independently to
    each grid cell before the output projection.

    Inputs:
        x: [batch_size, seq_len, height, width, input_channels]

    Outputs:
        y_hat: Raw logits of shape [batch_size, horizon, height, width, output_channels]
    """
    def __init__(self, config: ForecasterConfig) -> None:
        """
        Initialize the 2D ConvLSTM forecaster with the input configuration.
        
        Constructs a two-layer ConvLSTM2d with dropout regularization and a
        convolutional projection head for forecasting.
        
        Inputs:
            config (ForecasterConfig): Model configuration specifying
                - input_channels: Number of input features
                - horizon: Forecast horizon
                - output_channels: Number of output channels (defaults to 1)
                - hidden_size_1: Hidden dimension of first ConvLSTM2d
                - hidden_size_2: Hidden dimension of second ConvLSTM2d
                - use_bilstm: Whether to enable the per-cell BiLSTM
                - bilstm_hidden_size: Hidden size per BiLSTM direction
                - use_biconvlstm: Whether to enable the BiConvLSTM layer
                - biconvlstm_hidden_size: Hidden size per BiConvLSTM direction
                - biconvlstm_kernel_size: Kernel size used by the BiConvLSTM cells
                - dropout: Dropout probability
        """
        super().__init__()
        config = _backfill_config_defaults(config)
        if config.use_bilstm and config.use_biconvlstm:
            raise ValueError(
                "use_bilstm and use_biconvlstm cannot both be True; "
                "at most one optional temporal layer may be active."
            )

        self.config = config
        self.input_channels = config.input_channels
        self.horizon = config.horizon
        self.output_channels = config.output_channels
        self.use_bilstm = config.use_bilstm
        self.use_biconvlstm = config.use_biconvlstm

        self.convlstm1 = ConvLSTMCell(
            input_channels=self.input_channels,
            hidden_channels=config.hidden_size_1,
            attention=config.attention if 1 in config.attention_layers else "none",
            footprint=config.footprint,
            dilation=config.dilation,
            share_planes=config.share_planes,
        )
        self.dropout1 = nn.Dropout2d(config.dropout)

        self.convlstm2 = ConvLSTMCell(
            input_channels=config.hidden_size_1,
            hidden_channels=config.hidden_size_2,
            attention=config.attention if 2 in config.attention_layers else "none",
            footprint=config.footprint,
            dilation=config.dilation,
            share_planes=config.share_planes,
        )
        self.dropout2 = nn.Dropout2d(config.dropout)

        if self.use_bilstm:
            self.bilstm = PerCellBiLSTMLayer(
                input_size=config.hidden_size_2,
                hidden_size=config.bilstm_hidden_size,
            )
        else:
            self.bilstm = None

        if self.use_biconvlstm:
            self.biconvlstm = BiConvLSTMLayer(
                input_channels=config.hidden_size_2,
                hidden_channels=config.biconvlstm_hidden_size,
                kernel_size=config.biconvlstm_kernel_size,
            )
        else:
            self.biconvlstm = None

        active_layer = self.temporal_layer
        projection_input_channels = (
            active_layer.output_size if active_layer is not None else config.hidden_size_2
        )

        self.projection = nn.Conv2d(
            projection_input_channels,
            self.horizon * self.output_channels,
            kernel_size=1
        )

    @property
    def temporal_layer(self) -> Optional[nn.Module]:
        """Whichever optional temporal refinement layer is active, or ``None``.

        A plain property (not a registered submodule) so the active layer is
        not duplicated under a second name in ``state_dict``.
        """
        if self.bilstm is not None:
            return self.bilstm
        return self.biconvlstm

    def _run_cell(
        self,
        cell: ConvLSTMCell,
        x_t: Tensor,
        state: Optional[Tuple[Tensor, Tensor]],
    ) -> Tuple[Tensor, Tuple[Tensor, Tensor]]:
        """Advance one ConvLSTM timestep, optionally under gradient checkpointing.

        Checkpointing trades a recomputation of this single step's forward pass
        during backprop for not storing its activations, which is what keeps the
        unrolled sequence (seq_len steps x the patchwise-attention gate) from
        exhausting GPU memory. It is engaged only for attention cells, and only
        while training with autograd enabled; convolutional-gate cells, inference
        and the ``grad_checkpointing=False`` config all run the cell directly so
        the plain baseline pays no recomputation cost.
        """
        use_ckpt = (
            self.config.grad_checkpointing
            and cell.attention != "none"
            and self.training
            and torch.is_grad_enabled()
        )
        if not use_ckpt:
            return cell(x_t, state)

        # checkpoint() needs tensor args, so materialise the zero state that the
        # cell would otherwise create internally on the first step.
        if state is None:
            zeros = torch.zeros(
                x_t.size(0), cell.hidden_channels, x_t.size(2), x_t.size(3),
                device=x_t.device, dtype=x_t.dtype,
            )
            h, c = zeros, zeros.clone()
        else:
            h, c = state

        def _step(x_in: Tensor, h_in: Tensor, c_in: Tensor) -> Tuple[Tensor, Tensor]:
            _, (h_out, c_out) = cell(x_in, (h_in, c_in))
            return h_out, c_out

        h_new, c_new = checkpoint(_step, x_t, h, c, use_reentrant=False)
        return h_new, (h_new, c_new)

    def forward(self, x: Tensor) -> Tensor:
        """
        Forward pass through the 2D ConvLSTM forecaster.
        
        Processes input grid sequences through two stacked ConvLSTM2d layers,
        optionally applies the imported per-cell BiLSTM layer, and projects to
        the configured prediction horizon.
        
        Processing Steps:
            1. Reshape input
            2. Process timesteps through ConvLSTM1
            3. Apply dropout
            4. Process through ConvLSTM2
            5. Apply dropout
            6. Optionally apply the active temporal layer (per-cell BiLSTM or BiConvLSTM)
            7. Conv2d projection
            8. Reshape
        
        Inputs:
            x (Tensor): Input grid sequence of shape [batch_size, seq_len, height, width, input_channels]
        
        Outputs:
            y_hat (Tensor): Raw 'is burning' logits of shape [batch_size, 1, height, width, 1].
        """
        if x.ndim != 5:
            raise ValueError(
                "Expected input with shape [batch, time, height, width, channels], "
                f"but received {tuple(x.shape)}."
            )

        batch_size, seq_len, grid_height, grid_width, input_channels = x.shape

        if seq_len < 1:
            raise ValueError("Input sequence must contain at least one timestep.")

        if input_channels != self.input_channels:
            raise ValueError(
                "Input channel count does not match the model configuration. "
                f"Expected {self.input_channels} channels, but received {input_channels}."
            )
    
        # Reshape
        x = x.permute(0, 1, 4, 2, 3)
        
        # First ConvLSTM2d processes all timesteps
        h1_state = None
        h1_outputs = []
        for t in range(seq_len):
            h1, h1_state = self._run_cell(self.convlstm1, x[:, t, :, :, :], h1_state)
            h1_outputs.append(h1)

        h1_outputs_dropped = [self.dropout1(h) for h in h1_outputs]

        # Second ConvLSTM2d processes first layer outputs
        active_layer = self.temporal_layer
        h2_state = None
        h2_outputs = []
        for t in range(seq_len):
            h2, h2_state = self._run_cell(self.convlstm2, h1_outputs_dropped[t], h2_state)

            if active_layer is not None:
                h2_outputs.append(self.dropout2(h2))

        if active_layer is not None:
            # [B, T, hidden_size_2, H, W] -> [B, 2*hidden_size, H, W]
            temporal_features = active_layer(torch.stack(h2_outputs, dim=1))
        else:
            temporal_features = self.dropout2(h2)
        
        # Project to horizon * output_channels:
        # [B, temporal_features, H, W] -> [B, H*O, H, W]
        proj = self.projection(temporal_features)
        
        # Reshape to [B, H, H, W, O]
        proj = proj.view(batch_size, self.horizon, self.output_channels, grid_height, grid_width)
        y_hat = proj.permute(0, 1, 3, 4, 2)
        
        return y_hat

    def predict(self, x: Tensor) -> Tensor:
        """
        Generate predictions without computing gradients.
        Wrapper around forward() that sets the model to evaluation mode
        and disables gradient computation.
        
        Inputs:
            x (Tensor): Input grid sequence of shape [batch_size, seq_len, height, width, input_channels]
        
        Outputs:
            y_hat (Tensor): Burning probabilities between 0 and 1 with shape [batch_size, 1, height, width, 1].
        """
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            return torch.sigmoid(logits)

    def save(self, path: str) -> None:
        """
        Save the model checkpoint to disk.
        Saves both model weights (state_dict) and configuration to enable
        complete model reconstruction during loading.
        
        Inputs:
            path (str): Path where to save the checkpoint (.pth file).
        """
        torch.save(
            {
                "model_state_dict": self.state_dict(),
                "config": self.config,
            },
            path
        )

    @classmethod
    def load(cls, path: str, map_location: Optional[str] = None):
        """
        Load a trained model from a checkpoint file.
        
        Reconstructs the model architecture from saved configuration and
        restores trained weights. Automatically sets model to evaluation mode.
        
        Inputs:
            path (str): Path to the model checkpoint (.pth file). 
            map_location (Optional[str]): Device to load the model onto.
        
        Returns:
            MultivariateTSForecaster: Loaded model in evaluation mode, ready for inference.
        
        Raises:
            FileNotFoundError: If checkpoint file doesn't exist
            RuntimeError: If checkpoint is corrupted or incompatible
        """
        checkpoint = torch.load(path, map_location=map_location, weights_only=False)
        model = cls(checkpoint["config"])
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        return model
