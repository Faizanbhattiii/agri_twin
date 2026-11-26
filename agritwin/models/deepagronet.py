"""
DeepAgroNet: Deep Multimodal Spatiotemporal Neural Network for Crop Yield Forecasting.
Architecture:
1. 1D-CNN temporal feature extractors for 27-week agronomic phenological patterns.
2. Bidirectional LSTM with Temporal Attention Pooling capturing sequential crop growth dynamics.
3. Static Multilayer Perceptron (MLP) for soil pedological properties and geospatial factors.
4. Multimodal Fusion Head with calibrated Gaussian uncertainty estimation (mean and std).
"""

from typing import Dict, Optional, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from agritwin.features.pipeline import SEASON_WEEKS, TEMPORAL_FEATURE_NAMES, STATIC_FEATURE_NAMES
from agritwin.models.metrics import to_maund_per_acre, to_kg_per_ha


class TemporalAttention(nn.Module):
    """Temporal attention pooling across the 27 weekly timesteps."""

    def __init__(self, hidden_dim: int) -> None:
        super().__init__()
        self.attn = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.Tanh(),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # x shape: (batch_size, seq_len, hidden_dim)
        scores = self.attn(x)  # (batch_size, seq_len, 1)
        weights = F.softmax(scores, dim=1)  # (batch_size, seq_len, 1)
        pooled = torch.sum(x * weights, dim=1)  # (batch_size, hidden_dim)
        return pooled, weights.squeeze(-1)


class DeepAgroNet(nn.Module):
    """
    Multimodal PyTorch Model combining 1D-CNN, BiLSTM, and Soil MLP branches.
    Predicts wheat yield (kg/ha) with calibrated uncertainty bounds.
    """

    def __init__(
        self,
        num_temporal_features: int = len(TEMPORAL_FEATURE_NAMES),  # 10
        num_static_features: int = len(STATIC_FEATURE_NAMES),      # 9
        cnn_channels: int = 32,
        lstm_hidden: int = 64,
        lstm_layers: int = 2,
        static_hidden: int = 32,
        fusion_hidden: int = 64,
        dropout: float = 0.15,
    ) -> None:
        super().__init__()

        self.num_temporal_features = num_temporal_features
        self.num_static_features = num_static_features

        # 1. 1D-CNN temporal branch: (B, C_in, L) -> (B, C_out, L)
        self.conv1 = nn.Conv1d(
            in_channels=num_temporal_features,
            out_channels=cnn_channels,
            kernel_size=3,
            padding=1,
        )
        self.bn_conv1 = nn.BatchNorm1d(cnn_channels)

        self.conv2 = nn.Conv1d(
            in_channels=cnn_channels,
            out_channels=cnn_channels * 2,  # 64
            kernel_size=3,
            padding=1,
        )
        self.bn_conv2 = nn.BatchNorm1d(cnn_channels * 2)

        # 2. Bidirectional LSTM
        self.bilstm = nn.LSTM(
            input_size=cnn_channels * 2,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if lstm_layers > 1 else 0.0,
        )
        # BiLSTM output dim = lstm_hidden * 2 = 128
        self.attention = TemporalAttention(hidden_dim=lstm_hidden * 2)

        # 3. Static MLP branch for soil and geo properties
        self.static_mlp = nn.Sequential(
            nn.Linear(num_static_features, static_hidden),
            nn.BatchNorm1d(static_hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(static_hidden, static_hidden),
            nn.ReLU(),
        )

        # 4. Multimodal Fusion Head
        combined_dim = (lstm_hidden * 2) + static_hidden  # 128 + 32 = 160
        self.fusion_fc1 = nn.Linear(combined_dim, fusion_hidden)
        self.bn_fusion = nn.BatchNorm1d(fusion_hidden)
        self.fusion_fc2 = nn.Linear(fusion_hidden, 32)
        self.dropout = nn.Dropout(dropout)

        # 5. Prediction Heads: Mean (mu) and Standard Deviation (sigma)
        self.mean_head = nn.Linear(32, 1)
        self.logvar_head = nn.Linear(32, 1)

        # 6. Target Rescaling Buffers
        self.register_buffer("target_mean", torch.tensor(0.0, dtype=torch.float32))
        self.register_buffer("target_std", torch.tensor(1.0, dtype=torch.float32))

    def set_target_normalizer(self, target_mean: float, target_std: float) -> None:
        """Configure target rescaling parameters."""
        self.target_mean = torch.tensor(float(target_mean), dtype=torch.float32)
        self.target_std = torch.tensor(float(target_std), dtype=torch.float32)

    def forward(
        self,
        temporal_x: torch.Tensor,
        static_x: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass.

        Parameters:
            temporal_x: Tensor of shape (B, 27, 10)
            static_x: Tensor of shape (B, 9)

        Returns:
            mu: Predicted mean yield in kg/ha (B, 1)
            sigma: Predicted standard deviation (B, 1)
            attn_weights: Attention weights over 27 weeks (B, 27)
        """
        # CNN expects (B, channels, seq_len)
        cnn_in = temporal_x.transpose(1, 2)
        h = F.relu(self.bn_conv1(self.conv1(cnn_in)))
        h = self.dropout(h)
        h = F.relu(self.bn_conv2(self.conv2(h)))
        h = self.dropout(h)

        # Transpose back to (B, seq_len, channels) for BiLSTM
        lstm_in = h.transpose(1, 2)
        lstm_out, _ = self.bilstm(lstm_in)  # (B, 27, 128)

        # Attention pooling
        temporal_emb, attn_weights = self.attention(lstm_out)  # (B, 128), (B, 27)

        # Static soil embedding
        static_emb = self.static_mlp(static_x)  # (B, 32)

        # Fusion
        fused = torch.cat([temporal_emb, static_emb], dim=1)  # (B, 160)
        fused = F.relu(self.bn_fusion(self.fusion_fc1(fused)))
        fused = self.dropout(fused)
        fused = F.relu(self.fusion_fc2(fused))

        # Prediction
        mu = self.mean_head(fused)
        # Constrain standard deviation to be strictly positive
        log_var = self.logvar_head(fused)
        sigma = F.softplus(log_var) + 1e-3

        return mu, sigma, attn_weights

    def predict_yield(
        self,
        temporal_x: torch.Tensor,
        static_x: torch.Tensor,
        confidence_level: float = 0.95,
    ) -> Dict[str, np.ndarray]:
        """
        Inference helper with uncertainty quantification.
        Returns dict with predictions and bounds in both kg/ha and maund/acre.
        """
        self.eval()
        with torch.no_grad():
            mu_t, sigma_t, attn_t = self.forward(temporal_x, static_x)

            # Rescale if target normalizer is set
            t_mean = float(self.target_mean.item())
            t_std = float(self.target_std.item())
            if t_mean > 0.0:
                mu_t = mu_t * t_std + t_mean
                sigma_t = sigma_t * t_std

            mu = mu_t.cpu().numpy().flatten()
            sigma = sigma_t.cpu().numpy().flatten()
            attn = attn_t.cpu().numpy()

            # Z-score for confidence level (e.g., 1.96 for 95%)
            z = 1.96 if confidence_level == 0.95 else 1.645

            lower_kgha = np.maximum(0.0, mu - z * sigma)
            upper_kgha = mu + z * sigma

            return {
                "yield_kgha": mu,
                "sigma_kgha": sigma,
                "lower_kgha": lower_kgha,
                "upper_kgha": upper_kgha,
                "yield_maund_acre": to_maund_per_acre(mu),
                "lower_maund_acre": to_maund_per_acre(lower_kgha),
                "upper_maund_acre": to_maund_per_acre(upper_kgha),
                "attention_weights": attn,
            }


def gaussian_nll_loss(
    mu: torch.Tensor,
    sigma: torch.Tensor,
    target: torch.Tensor,
) -> torch.Tensor:
    """
    Heteroscedastic Gaussian Negative Log-Likelihood loss:
    NLL = 0.5 * log(sigma^2) + 0.5 * (target - mu)^2 / sigma^2
    """
    var = sigma ** 2
    loss = 0.5 * torch.log(var) + 0.5 * ((target - mu) ** 2) / (var + 1e-6)
    return torch.mean(loss)
