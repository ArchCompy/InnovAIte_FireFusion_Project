"""
Patchwise self-attention operator for ConvLSTM gates.

Implements Eq. 13 of Masrur et al. (2024, Ecological Informatics 82:102760),
which replaces the gate convolution inside a ConvLSTM cell:

    Y_i = sum_{j in R_i} [ alpha(X_{R_i})_j (*) beta(x_j) ]

R_i is the footprint (patch) around cell i, beta transforms each cell in the
patch into a value vector, and alpha produces the mixing weights from the whole
patch rather than from individual pairs. The concrete forms of alpha and beta
follow the self-attention network (SAN) formulation of Zhao et al. (2020),
which the paper cites as its source but does not reproduce.
"""
from typing import Optional

import torch
from torch import Tensor, nn


class PatchwiseAttention2d(nn.Module):
    """
    Content-adaptive drop-in replacement for the ConvLSTM gate convolution.

    Matches the call signature of nn.Conv2d(in_channels, out_channels, k,
    padding=k//2): takes [B, in_channels, H, W], returns [B, out_channels, H, W].

    Unlike a convolution, whose weights depend only on a neighbour's *position*
    in the kernel, the weights here depend on the *content* of the patch, so the
    operator can weight (for example) downwind neighbours more strongly where
    the wind field says so.

    Attributes:
        footprint (int): Side length of the square patch R_i. Must be odd.
        dilation (int): Spacing between sampled cells. A footprint of 7 with
            dilation 2 reaches +/-6 cells at the memory cost of a 7x7 patch.
        share_planes (int): Number of output channels sharing one set of
            attention weights. Must divide out_channels.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        footprint: int = 7,
        dilation: int = 1,
        share_planes: int = 8,
        mid_channels: Optional[int] = None,
    ) -> None:
        super().__init__()
        if footprint % 2 == 0:
            raise ValueError(f"footprint must be odd, got {footprint}")
        if out_channels % share_planes != 0:
            raise ValueError(
                f"out_channels ({out_channels}) must be divisible by "
                f"share_planes ({share_planes})"
            )

        self.footprint = footprint
        self.out_channels = out_channels
        self.share_planes = share_planes
        self.n_positions = footprint * footprint
        self.mid = mid_channels or max(out_channels // 4, 8)

        # beta: per-cell value transform
        self.value = nn.Conv2d(in_channels, out_channels, kernel_size=1)

        # alpha: whole patch -> one weight per (patch position, channel group)
        self.embed = nn.Conv2d(in_channels, self.mid, kernel_size=1)
        self.alpha = nn.Sequential(
            nn.Conv2d(self.mid * self.n_positions, self.mid, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(
                self.mid,
                self.n_positions * (out_channels // share_planes),
                kernel_size=1,
            ),
        )

        self.unfold = nn.Unfold(
            kernel_size=footprint,
            dilation=dilation,
            padding=dilation * (footprint // 2),
        )

    def forward(self, x: Tensor) -> Tensor:
        """
        Inputs:
            x (Tensor): [batch, in_channels, height, width]

        Outputs:
            Tensor: [batch, out_channels, height, width]
        """
        batch_size, _, height, width = x.shape
        n_cells = height * width
        n_pos = self.n_positions
        n_groups = self.out_channels // self.share_planes

        # beta(x_j) for every cell of every patch
        values = self.unfold(self.value(x))
        values = values.view(batch_size, n_groups, self.share_planes, n_pos, n_cells)

        # alpha(X_{R_i}): the flattened patch at each location -> patch weights
        patch = self.unfold(self.embed(x)).view(
            batch_size, self.mid * n_pos, height, width
        )
        weights = self.alpha(patch).view(batch_size, n_groups, n_pos, n_cells)
        weights = torch.softmax(weights, dim=2).unsqueeze(2)

        out = (weights * values).sum(dim=3)
        return out.reshape(batch_size, self.out_channels, height, width)