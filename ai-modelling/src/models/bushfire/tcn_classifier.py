"""
FireFusion — TCN Classifier Architecture
=========================================
Location : src/models/bushfire/tcn_classifier.py

Defines the TCN model architecture only.
No data loading, no training logic, no config constants.

Imported by:
    src/training/train_classifier.py
    src/models/bushfire/classification_inference.py
"""

from dataclasses import dataclass, field
import torch
import torch.nn as nn


@dataclass
class ClassifierConfig:
    """
    All architecture hyperparameters in one place.
    Pass an instance of this to TCNClassifier.__init__.

    Dilations are auto-set as dilation_base^i per block:
        6 blocks, base=2 → dilations 1, 2, 4, 8, 16, 32
        Receptive field = 2 * (kernel_size-1) * sum(dilations) = 252 steps
    """
    n_features:    int        = 7
    lookback_steps: int       = 60
    channels:      list       = field(default_factory=lambda: [64, 64, 64, 64, 64, 64])
    kernel_size:   int        = 3
    dilation_base: int        = 2
    dropout:       float      = 0.2


class CausalConv1d(nn.Module):
    """
    Dilated causal convolution.
    Left-pads only — future timesteps are never seen by the model.
    """
    def __init__(self, in_ch: int, out_ch: int, kernel_size: int, dilation: int):
        super().__init__()
        self.padding = (kernel_size - 1) * dilation
        self.conv    = nn.Conv1d(
            in_ch, out_ch, kernel_size,
            padding=0, dilation=dilation
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(nn.functional.pad(x, (self.padding, 0)))


class TCNBlock(nn.Module):
    """
    Residual dilated TCN block:
        CausalConv → BatchNorm → ReLU → Dropout  (×2)
        + residual 1×1 conv if channel dimensions differ
    """
    def __init__(self, in_ch: int, out_ch: int,
                 kernel_size: int, dilation: int, dropout: float):
        super().__init__()
        self.conv1 = CausalConv1d(in_ch,  out_ch, kernel_size, dilation)
        self.conv2 = CausalConv1d(out_ch, out_ch, kernel_size, dilation)
        self.norm1 = nn.BatchNorm1d(out_ch)
        self.norm2 = nn.BatchNorm1d(out_ch)
        self.relu  = nn.ReLU()
        self.drop  = nn.Dropout(dropout)
        self.residual_conv = (
            nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = self.residual_conv(x)
        out = self.drop(self.relu(self.norm1(self.conv1(x))))
        out = self.drop(self.relu(self.norm2(self.conv2(out))))
        return self.relu(out + res)


class TCNClassifier(nn.Module):
    """
    Full TCN for binary fire occurrence classification.

    Input  : (batch, n_features, lookback_steps)
    Output : (batch, 1) — fire probability in [0, 1] via sigmoid

    Architecture:
        Stack of TCNBlock (exponentially increasing dilation)
        → AdaptiveAvgPool1d (collapse time dimension)
        → Linear(32) → ReLU → Dropout
        → Linear(1)  → Sigmoid
    """
    def __init__(self, config: ClassifierConfig = None):
        super().__init__()
        if config is None:
            config = ClassifierConfig()

        self.config = config
        layers, in_ch = [], config.n_features

        for i, out_ch in enumerate(config.channels):
            dilation = config.dilation_base ** i
            layers.append(
                TCNBlock(in_ch, out_ch, config.kernel_size, dilation, config.dropout)
            )
            in_ch = out_ch

        self.tcn  = nn.Sequential(*layers)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(config.channels[-1], 32),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, n_features, lookback)
        x = self.tcn(x)   # (batch, channels, lookback)
        x = self.pool(x)  # (batch, channels, 1)
        return self.head(x)  # (batch, 1)

    def parameter_count(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def receptive_field(self) -> int:
        cfg = self.config
        return 2 * (cfg.kernel_size - 1) * sum(
            cfg.dilation_base ** i for i in range(len(cfg.channels))
        )
