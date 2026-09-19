"""Reusable bidirectional LSTM layers for bushfire forecasting models."""

import torch
from torch import Tensor, nn


class PerCellBiLSTMLayer(nn.Module):
    """Apply one shared BiLSTM independently to every spatial grid cell.

    The layer accepts ConvLSTM features in ``[B, T, C, H, W]`` format and
    returns the concatenated final forward and backward states in
    ``[B, 2 * hidden_size, H, W]`` format. Grid cells never mix with one
    another inside this layer; they all reuse the same BiLSTM weights.
    """

    def __init__(self, input_size: int, hidden_size: int) -> None:
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.bilstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            batch_first=True,
            bidirectional=True,
        )

    @property
    def output_size(self) -> int:
        """Number of output channels after joining both directions."""
        return 2 * self.hidden_size

    def forward(self, x: Tensor) -> Tensor:
        """Encode each cell's temporal sequence with shared weights."""
        if x.ndim != 5:
            raise ValueError(
                "Expected ConvLSTM features with shape [batch, time, channels, "
                f"height, width], but received {tuple(x.shape)}."
            )

        batch_size, seq_len, channels, grid_height, grid_width = x.shape

        if seq_len < 1:
            raise ValueError("Input sequence must contain at least one timestep.")

        if channels != self.input_size:
            raise ValueError(
                "Feature channel count does not match the BiLSTM configuration. "
                f"Expected {self.input_size} channels, but received {channels}."
            )

        # [B, T, C, H, W] -> [B*H*W, T, C]. Each row is the temporal
        # sequence of one cell; the same BiLSTM parameters process every row.
        sequence = x.permute(0, 3, 4, 1, 2).reshape(
            batch_size * grid_height * grid_width,
            seq_len,
            channels,
        )

        _, (h_n, _) = self.bilstm(sequence)
        summary = torch.cat([h_n[0], h_n[1]], dim=1)

        # [B*H*W, 2*hidden] -> [B, 2*hidden, H, W]
        return summary.reshape(
            batch_size,
            grid_height,
            grid_width,
            self.output_size,
        ).permute(0, 3, 1, 2)
