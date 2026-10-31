"""Wavelengths of mercury lines from automated fringe counts.

When the movable mirror moves by d, the path difference changes by 2d and N dark fringes pass:
2d = N * lambda. The mirror is driven by a micrometer through a lever, d = R * (micrometer
displacement), where the reduction factor R is calibrated with the mercury green line.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from .fringes import count_with_uncertainty
from .tracker import brightness

DATA_DIR = Path("data")
GREEN_NM = 546.0735  # calibration line

# NIST wavelengths of the measured lines (the yellow doublet is reported as its mean)
REFERENCE_NM = {"Hg green": 546.0735, "Hg blue": 435.8328, "Hg yellow": (576.9598 + 579.0663) / 2}

# Reading uncertainty of each micrometer reading, in mm (half of the 0.01 mm scale division)
MICROMETER_READING_UNC_MM = 0.005

# Reduction factor obtained in the 2019 report from the manual calibration (Figure 4)
REPORT_REDUCTION_FACTOR = (0.1992, 0.0007)


def load_clips(data_dir=DATA_DIR):
    with open(Path(data_dir) / "clips.csv", newline="") as f:
        return list(csv.DictReader(f))


def count_all(clips, data_dir=DATA_DIR):
    """Count fringes in every tracked clip."""
    for clip in clips:
        signal = brightness(Path(data_dir) / "tracker" / clip["file"], clip["region"])
        clip["fringes"], clip["fringes_unc"] = count_with_uncertainty(signal)
        clip["frames"] = len(signal)
    return clips


def per_video(clips):
    """Combine several trackings of the same video into one measurement per video.

    Trackings of one video are not independent, so the uncertainty is not reduced by averaging;
    their disagreement is added as an extra uncertainty instead.
    """
    groups = defaultdict(list)
    for clip in clips:
        if clip["use"] == "yes":
            groups[(clip["source"], clip["video"])].append(clip)
    videos = []
    for (source, video), trackings in groups.items():
        counts = np.array([c["fringes"] for c in trackings], dtype=float)
        unc = max(c["fringes_unc"] for c in trackings)
        displacement = float(trackings[0]["micrometer_end_mm"]) - float(trackings[0]["micrometer_start_mm"])
        videos.append({
            "source": source, "video": video, "trackings": len(trackings),
            "fringes": float(counts.mean()), "fringes_unc": float(np.hypot(unc, (counts.max() - counts.min()) / 2)),
            "micrometer_mm": displacement,
            "micrometer_unc_mm": MICROMETER_READING_UNC_MM * np.sqrt(2),
        })
    return videos


def reduction_factor(green_videos):
    """R from the green calibration clips: R = N * lambda_green / (2 * micrometer displacement)."""
    values, uncs = [], []
    for v in green_videos:
        r = v["fringes"] * GREEN_NM * 1e-6 / (2 * v["micrometer_mm"])
        rel = np.hypot(v["fringes_unc"] / v["fringes"], v["micrometer_unc_mm"] / v["micrometer_mm"])
        values.append(r)
        uncs.append(r * rel)
    return weighted_mean(values, uncs)


def weighted_mean(values, uncertainties):
    w = 1 / np.square(uncertainties)
    return float(np.sum(w * values) / np.sum(w)), float(1 / np.sqrt(np.sum(w)))


def wavelength_nm(video, r, r_unc):
    """lambda = 2 R (micrometer displacement) / N, with uncertainties propagated in quadrature."""
    value = 2 * r * video["micrometer_mm"] / video["fringes"] * 1e6
    rel = np.sqrt((r_unc / r) ** 2 + (video["micrometer_unc_mm"] / video["micrometer_mm"]) ** 2
                  + (video["fringes_unc"] / video["fringes"]) ** 2)
    return value, value * rel


def analyse(out_dir="results", data_dir=DATA_DIR, make_plots=True):
    clips = count_all(load_clips(data_dir), data_dir)
    videos = per_video(clips)

    print("Fringes counted in each tracked clip:")
    for clip in clips:
        used = "" if clip["use"] == "yes" else "  (not used: no micrometer readings)"
        print(f"  {clip['file']:24s} {clip['source']:10s} {clip['fringes']:4d} ± {clip['fringes_unc']:.1f}{used}")

    green = [v for v in videos if v["source"] == "Hg green"]
    calibrations = {
        "automated (green clip)": reduction_factor(green),
        "report (manual)": REPORT_REDUCTION_FACTOR,
    }
    r, r_unc = calibrations["automated (green clip)"]
    print(f"\nReduction factor from the green clip: R = {r:.4f} ± {r_unc:.4f}"
          f"   (2019 report: {REPORT_REDUCTION_FACTOR[0]} ± {REPORT_REDUCTION_FACTOR[1]})")

    results = {"reduction_factor": {k: list(v) for k, v in calibrations.items()}, "wavelengths": {}, "clips": [], "videos": videos}
    for source in ["Hg blue", "Hg yellow"]:
        results["wavelengths"][source] = {"reference_nm": REFERENCE_NM[source]}
        for name, (rv, ru) in calibrations.items():
            measurements = [wavelength_nm(v, rv, ru) for v in videos if v["source"] == source]
            value, unc = weighted_mean([m[0] for m in measurements], [m[1] for m in measurements])
            results["wavelengths"][source][name] = [value, unc]
        value, unc = results["wavelengths"][source]["automated (green clip)"]
        pull = (value - REFERENCE_NM[source]) / unc
        print(f"{source:10s} lambda = {value:5.1f} ± {unc:4.1f} nm   NIST {REFERENCE_NM[source]:.1f} nm   ({pull:+.1f} sigma)")

    results["clips"] = [{k: c[k] for k in ("file", "region", "source", "video", "use", "fringes", "fringes_unc", "frames")} for c in clips]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, indent=2, default=float))
    if make_plots:
        from . import plots
        plots.make_all(clips, results, out, data_dir)
        print(f"\nWrote {out / 'results.json'} and figures to {out}/")
    return results
