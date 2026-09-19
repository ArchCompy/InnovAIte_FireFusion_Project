"""Shared 2D ConvLSTM cell used by the forecaster and its optional layers."""
from typing import Optional, Tuple

import torch
from torch import Tensor, nn

from .attention import PatchwiseAttention2d


class ConvLSTMCell(nn.Module):
    """2D ConvLSTM cell for spatiotemporal data.

    The four gates (input, forget, candidate, output) are produced by a single
    gate operator over the channel-wise concatenation of the input and the
    previous hidden state. That operator is a standard :class:`~torch.nn.Conv2d`
    when ``attention="none"``, or the content-adaptive
    :class:`PatchwiseAttention2d` when ``attention="patchwise"`` (Masrur et al.,
    2024), which replaces position-indexed convolution weights with weights that
    depend on the contents of each cell's spatial patch.
    """

    def __init__(
        self,
        input_channels: int,
        hidden_channels: int,
        kernel_size: int = 3,
        attention: str = "none",
        footprint: int = 7,
        dilation: int = 1,
        share_planes: int = 8,
    ) -> None:
        """Build a ConvLSTM cell with either a convolutional or attention gate.

        Inputs:
            input_channels (int): Channels of the per-timestep input ``x``.
            hidden_channels (int): Channels of the hidden/cell state.
            kernel_size (int): Convolution kernel size for the ``"none"`` gate.
            attention (str): Gate operator. ``"none"`` uses a standard
                ``Conv2d``; ``"patchwise"`` uses :class:`PatchwiseAttention2d`.
            footprint (int): Patch side length for patchwise attention (odd).
            dilation (int): Spacing between sampled cells in the attention patch.
            share_planes (int): Output channels sharing one attention weight set.
        """
        super().__init__()
        self.input_channels = input_channels
        self.hidden_channels = hidden_channels
        self.attention = attention

        combined_channels = input_channels + hidden_channels
        gate_channels = 4 * hidden_channels

        # Exactly one gate operator is created; forward() uses whichever exists.
        # Keeping the convolutional path under ``self.conv`` preserves the
        # state_dict keys of checkpoints trained before attention was added.
        if attention == "none":
            self.conv = nn.Conv2d(
                combined_channels,
                gate_channels,
                kernel_size,
                padding=kernel_size // 2,
            )
            self.attn: Optional[nn.Module] = None
        elif attention == "patchwise":
            self.conv = None
            self.attn = PatchwiseAttention2d(
                in_channels=combined_channels,
                out_channels=gate_channels,
                footprint=footprint,
                dilation=dilation,
                share_planes=share_planes,
            )
        else:
            raise ValueError(
                f"Unknown attention mode {attention!r}; expected 'none' or 'patchwise'."
            )

    def forward(self, x: Tensor, states: Optional[Tuple[Tensor, Tensor]] = None) -> Tuple[Tensor, Tuple[Tensor, Tensor]]:
        """Forward pass of ConvLSTM2d cell."""
        if states is None:
            h = torch.zeros(x.size(0), self.hidden_channels, x.size(2), x.size(3), device=x.device, dtype=x.dtype)
            c = torch.zeros(x.size(0), self.hidden_channels, x.size(2), x.size(3), device=x.device, dtype=x.dtype)
        else:
            h, c = states

        combined = torch.cat([x, h], dim=1)
        gate_op = self.conv if self.conv is not None else self.attn
        gates = gate_op(combined)
        i, f, g, o = torch.split(gates, self.hidden_channels, dim=1)

        i = torch.sigmoid(i)
        f = torch.sigmoid(f)
        g = torch.tanh(g)
        o = torch.sigmoid(o)

        c_new = f * c + i * g
        h_new = o * torch.tanh(c_new)

        return h_new, (h_new, c_new)
