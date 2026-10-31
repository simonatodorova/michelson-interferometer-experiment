import numpy as np
import pytest

from michelson.analysis import GREEN_NM, analyse, reduction_factor, wavelength_nm
from michelson.fringes import count_fringes, count_with_uncertainty
from michelson.tracker import luma, rgb_regions


def synthetic_clip(n_fringes, frames_per_fringe=9.0, idle=80, noise=3.0, seed=0):
    """A pixel that sits still, then sees n_fringes pass with drifting brightness and contrast, then sits still."""
    rng = np.random.default_rng(seed)
    moving = int(n_fringes * frames_per_fringe)
    phase = np.linspace(0, 2 * np.pi * n_fringes, moving, endpoint=False) + np.pi  # starts and ends bright
    contrast = 40 + 25 * np.sin(np.linspace(0, 3, moving))
    baseline = 110 + 15 * np.linspace(-1, 1, moving)
    signal = baseline + contrast * np.cos(phase)
    still = np.full(idle, signal[0])
    return np.concatenate([still, signal, np.full(idle, signal[-1])]) + rng.normal(0, noise, moving + 2 * idle)


@pytest.mark.parametrize("n", [20, 75, 143, 180])
def test_counts_synthetic_fringes(n):
    assert abs(count_fringes(synthetic_clip(n)).n - n) <= 1


def test_idle_frames_are_not_counted():
    result = count_fringes(synthetic_clip(50, idle=300))
    assert abs(result.n - 50) <= 1
    assert not result.active[:200].any()


def test_uncertainty_has_one_in_fifty_floor():
    n, unc = count_with_uncertainty(synthetic_clip(150, noise=0.5))
    assert unc >= n / 50 - 1e-9


def test_reads_tracker_rgb_region():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<object class="org.opensourcephysics.cabrillo.tracker.TrackerPanel">
  <property name="tracks" type="collection">
    <item><object class="org.opensourcephysics.cabrillo.tracker.RGBRegion">
      <property name="name" type="string">region A</property>
      <property name="rgb" type="array" class="[[D">
        <property name="array" type="string">{{10.0,20.0,30.0,3.0},{100.0,200.0,50.0,3.0}}</property>
      </property>
    </object></item>
  </property>
</object>"""
    regions = rgb_regions(xml)
    assert list(regions) == ["region A"]
    assert regions["region A"].shape == (2, 4)
    assert luma(regions["region A"])[1] == pytest.approx(0.299 * 100 + 0.587 * 200 + 0.114 * 50)


def test_calibration_and_wavelength_round_trip():
    # A mirror moving 0.04 mm (R = 0.2, micrometer 0.2 mm) passes 2 * 0.04 mm / 546.07 nm = 146.5 green fringes
    green = {"fringes": 2 * 0.04e6 / GREEN_NM, "fringes_unc": 1.0, "micrometer_mm": 0.2, "micrometer_unc_mm": 0.001}
    r, r_unc = reduction_factor([green])
    assert r == pytest.approx(0.2)
    blue = {"fringes": 2 * 0.04e6 / 435.8, "fringes_unc": 1.0, "micrometer_mm": 0.2, "micrometer_unc_mm": 0.001}
    value, unc = wavelength_nm(blue, r, r_unc)
    assert value == pytest.approx(435.8)
    assert 0 < unc < 20


def test_full_analysis_on_included_data(tmp_path):
    results = analyse(tmp_path, make_plots=False)
    blue = results["wavelengths"]["Hg blue"]
    value, unc = blue["automated (green clip)"]
    assert abs(value - blue["reference_nm"]) < 2 * unc
    assert (tmp_path / "results.json").exists()
