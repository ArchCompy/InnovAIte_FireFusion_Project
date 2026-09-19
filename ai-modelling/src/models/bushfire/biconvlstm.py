"""Reusable Bidirectional ConvLSTM (BiConvLSTM) layer for bushfire forecasting models."""

import torch
from torch import Tensor, nn

from .convlstm import ConvLSTMCell


class BiConvLSTMLayer(nn.Module):
    """Run independent forward and backward ConvLSTM recurrences over a sequence.

    The layer accepts ConvLSTM features in ``[B, T, C, H, W]`` format. A
    forward :class:`ConvLSTMCell` reads the sequence ``t = 0 -> T-1`` and a
    separate backward cell reads it ``t = T-1 -> 0``; the two cells have
    independent weights. Unlike a per-cell BiLSTM, the convolutional gates let
    information propagate between neighbouring grid cells at every timestep.
    The final hidden states of both directions are concatenated on the
    channel axis, returning ``[B, 2 * hidden_channels, H, W]``.
    """

    def __init__(self, input_channels: int, hidden_channels: int, kernel_size: int = 3) -> None:
        super().__init__()
        if kernel_size <= 0 or kernel_size % 2 == 0:
            raise ValueError(
                f"kernel_size must be a positive odd number, but received {kernel_size}."
            )

        self.input_channels = input_channels
        self.hidden_channels = hidden_channels
        self.forward_cell = ConvLSTMCell(input_channels, hidden_channels, kernel_size)
        self.backward_cell = ConvLSTMCell(input_channels, hidden_channels, kernel_size)

    @property
    def output_size(self) -> int:
        """Number of output channels after joining both directions."""
        return 2 * self.hidden_channels

    def forward(self, x: Tensor) -> Tensor:
        """Encode the sequence with independent forward/backward ConvLSTM cells."""
        if x.ndim != 5:
            raise ValueError(
                "Expected ConvLSTM features with shape [batch, time, channels, "
                f"height, width], but received {tuple(x.shape)}."
            )

        batch_size, seq_len, channels, grid_height, grid_width = x.shape

        if seq_len < 1:
            raise ValueError("Input sequence must contain at least one timestep.")

        if channels != self.input_channels:
            raise ValueError(
                "Feature channel count does not match the BiConvLSTM configuration. "
                f"Expected {self.input_channels} channels, but received {channels}."
            )

        fwd_state = None
        for t in range(seq_len):
            h_fwd, fwd_state = self.forward_cell(x[:, t], fwd_state)

        bwd_state = None
        for t in reversed(range(seq_len)):
            h_bwd, bwd_state = self.backward_cell(x[:, t], bwd_state)

        return torch.cat([h_fwd, h_bwd], dim=1)
