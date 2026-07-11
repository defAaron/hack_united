"""Shared primitives for time-series signal analysis (audio + motion)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class TimeSeries:
    """A regularly-sampled 1D signal over time."""

    timestamps: np.ndarray  # seconds, shape (N,)
    values: np.ndarray  # normalized 0-1, shape (N,)


def normalize(values: np.ndarray) -> np.ndarray:
    """Min-max normalize a 1D array to the 0-1 range."""
    if values.size == 0:
        return values
    vmin, vmax = float(values.min()), float(values.max())
    if vmax - vmin < 1e-9:
        return np.zeros_like(values)
    return (values - vmin) / (vmax - vmin)
