from __future__ import annotations

import math

import torch
from torch import nn


class PositionalEncoding(nn.Module):
    def __init__(self, model_dim: int, max_len: int = 512) -> None:
        super().__init__()
        positions = torch.arange(max_len).unsqueeze(1)
        div_terms = torch.exp(torch.arange(0, model_dim, 2) * (-math.log(10000.0) / model_dim))
        encoding = torch.zeros(max_len, model_dim)
        encoding[:, 0::2] = torch.sin(positions * div_terms)
        encoding[:, 1::2] = torch.cos(positions * div_terms[: encoding[:, 1::2].shape[1]])
        self.register_buffer("encoding", encoding.unsqueeze(0))

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return values + self.encoding[:, : values.size(1)]


class TransformerAutoencoder(nn.Module):
    def __init__(
        self,
        input_dim: int,
        model_dim: int = 64,
        num_heads: int = 4,
        num_layers: int = 2,
        feedforward_dim: int = 128,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.input_projection = nn.Linear(input_dim, model_dim)
        self.position = PositionalEncoding(model_dim)
        self.attention_layers = nn.ModuleList(
            [nn.MultiheadAttention(model_dim, num_heads, dropout=dropout, batch_first=True) for _ in range(num_layers)]
        )
        self.norm_attention = nn.ModuleList([nn.LayerNorm(model_dim) for _ in range(num_layers)])
        self.feedforward = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Linear(model_dim, feedforward_dim),
                    nn.GELU(),
                    nn.Dropout(dropout),
                    nn.Linear(feedforward_dim, model_dim),
                )
                for _ in range(num_layers)
            ]
        )
        self.norm_feedforward = nn.ModuleList([nn.LayerNorm(model_dim) for _ in range(num_layers)])
        self.decoder = nn.Sequential(nn.Linear(model_dim, feedforward_dim), nn.GELU(), nn.Linear(feedforward_dim, input_dim))

    def encode(self, values: torch.Tensor, return_attention: bool = False) -> tuple[torch.Tensor, list[torch.Tensor]]:
        hidden = self.position(self.input_projection(values))
        attentions: list[torch.Tensor] = []
        for attention, norm_a, feedforward, norm_f in zip(
            self.attention_layers, self.norm_attention, self.feedforward, self.norm_feedforward
        ):
            attended, weights = attention(hidden, hidden, hidden, need_weights=True, average_attn_weights=False)
            hidden = norm_a(hidden + attended)
            hidden = norm_f(hidden + feedforward(hidden))
            if return_attention:
                attentions.append(weights.detach())
        return hidden, attentions

    def forward(self, values: torch.Tensor, return_attention: bool = False) -> tuple[torch.Tensor, list[torch.Tensor]]:
        hidden, attentions = self.encode(values, return_attention=return_attention)
        return self.decoder(hidden), attentions


def reconstruction_error(inputs: torch.Tensor, outputs: torch.Tensor) -> torch.Tensor:
    return torch.mean((inputs - outputs) ** 2, dim=(1, 2))

