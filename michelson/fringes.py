"""Automated fringe counting.

As the mirror moves, dark and bright fringes sweep across the tracked pixel and its brightness
oscillates. Each dark fringe is one brightness minimum. Because the overall brightness and the
fringe contrast drift during a clip (and drop to almost nothing near the beat nodes of a doublet),
the signal is first normalised to its local brightness envelope, then minima are found with a
prominence threshold. Frames where the pattern is not moving (before and after turning the
micrometer) have no oscillation and are excluded.
"""
from dataclasses import dataclass

import numpy as np
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d
from scipy.signal import find_peaks

# Counter settings: (envelope window in frames, minimum prominence of a dark fringe)
DEFAULT_SETTINGS = (31, 0.35)
# Alternative settings used to estimate how much the count depends on the counter itself
VARIED_SETTINGS = [(21, 0.30), (31, 0.35), (41, 0.40), (31, 0.50)]


@dataclass
class FringeCount:
    n: int
    minima: np.ndarray        # frame index of every dark fringe
    active: np.ndarray        # mask of frames where the pattern is moving
    normalised: np.ndarray    # brightness scaled to its local envelope (0 = dark, 1 = bright)
    envelope_low: np.ndarray
    envelope_high: np.ndarray


def envelope(signal, window):
    """Smoothed running minimum and maximum of a signal."""
    low = uniform_filter1d(minimum_filter1d(signal, window), window)
    high = uniform_filter1d(maximum_filter1d(signal, window), window)
    return low, high


def count_fringes(signal, window=DEFAULT_SETTINGS[0], prominence=DEFAULT_SETTINGS[1], active_fraction=0.35):
    """Count dark fringes (brightness minima) in a brightness time series."""
    signal = np.asarray(signal, dtype=float)
    low, high = envelope(signal, window)
    amplitude = high - low
    active = amplitude > active_fraction * np.percentile(amplitude, 90)
    normalised = (signal - low) / np.maximum(amplitude, 1e-9)
    minima, _ = find_peaks(-normalised, prominence=prominence)
    minima = minima[active[minima]]
    return FringeCount(len(minima), minima, active, normalised, low, high)


def count_with_uncertainty(signal, settings=VARIED_SETTINGS, relative_floor=1 / 50):
    """Fringe count and its uncertainty.

    The uncertainty combines the spread of counts across counter settings with a floor of one
    fringe in every fifty (the reading uncertainty used in the original report).
    """
    counts = np.array([count_fringes(signal, w, p).n for w, p in settings])
    nominal = count_fringes(signal).n
    spread = (counts.max() - counts.min()) / 2
    return nominal, float(np.hypot(spread, relative_floor * nominal))
