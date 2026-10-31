"""Figures for the fringe counting and the wavelength results."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .fringes import count_fringes
from .tracker import brightness

plt.rcParams.update({"font.size": 12, "axes.spines.top": False, "axes.spines.right": False})
COLOURS = {"Hg green": "#2ca25f", "Hg blue": "#3b6fd4", "Hg yellow": "#e3a600", "day 2": "#9c9ca1"}


def counting_plot(data_dir, out_path, file="green/IMG_6692.trk", fps=30.0):
    """Brightness of the tracked pixel with every counted dark fringe marked (cf. Figure 3 of the report)."""
    signal = brightness(Path(data_dir) / "tracker" / file)
    result = count_fringes(signal)
    t = np.arange(len(signal)) / fps

    fig, (ax, zoom) = plt.subplots(2, 1, figsize=(12, 7), gridspec_kw={"height_ratios": [2, 1.2], "hspace": 0.35})
    ax.fill_between(t, result.envelope_low, result.envelope_high, color="#2ca25f", alpha=0.12, label="local envelope")
    ax.plot(t, signal, color="#1b5e3b", lw=0.7, label="pixel brightness")
    ax.plot(t[result.minima], signal[result.minima], "v", color="#d7301f", ms=4, label=f"dark fringes ({result.n})")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Brightness")
    ax.set_title(f"Automated fringe count: Hg green line, micrometer 7.0 → 7.2 mm ({file.split('/')[-1]})", loc="left", fontsize=13, pad=30)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=11)

    window = slice(int(10 * fps), int(14 * fps))
    sel = result.minima[(result.minima >= window.start) & (result.minima < window.stop)]
    ax.axvspan(t[window.start], t[window.stop], color="grey", alpha=0.12)
    zoom.plot(t[window], signal[window], "o-", color="#1b5e3b", lw=0.8, ms=3)
    zoom.plot(t[sel], signal[sel], "v", color="#d7301f", ms=8)
    zoom.set_xlabel("Time [s] (zoom on the shaded region)")
    zoom.set_ylabel("Brightness")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def counts_plot(clips, out_path):
    """Fringe count of every tracked clip, coloured by light source."""
    fig, ax = plt.subplots(figsize=(13, 4.8))
    for i, clip in enumerate(clips):
        colour = COLOURS.get(clip["source"], "#9c9ca1")
        ax.bar(i, clip["fringes"], color=colour, alpha=1.0 if clip["use"] == "yes" else 0.35, edgecolor="none")
        ax.errorbar(i, clip["fringes"], yerr=clip["fringes_unc"], color="black", lw=0.8, capsize=2)
    ax.set_xticks(range(len(clips)))
    ax.set_xticklabels([c["file"].split("/")[-1].replace(".trk", "") for c in clips], rotation=70, fontsize=9)
    ax.set_ylabel("Dark fringes counted")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in COLOURS.values()]
    ax.legend(handles, list(COLOURS), frameon=False, ncol=4, loc="upper left")
    ax.set_title("Faded bars: clips without recorded micrometer readings (counted, not used)", loc="left", fontsize=11)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def wavelength_plot(results, out_path):
    fig, ax = plt.subplots(figsize=(9, 3.8))
    sources = list(results["wavelengths"])
    for i, source in enumerate(sources):
        entry = results["wavelengths"][source]
        y = len(sources) - i
        ax.plot([entry["reference_nm"]] * 2, [y - 0.35, y + 0.35], color="black", lw=2, label="NIST" if i == 0 else None)
        for offset, (name, marker) in zip([0.12, -0.12], [("automated (green clip)", "o"), ("report (manual)", "s")]):
            value, unc = entry[name]
            ax.errorbar(value, y + offset, xerr=unc, fmt=marker, color=COLOURS[source], capsize=4, ms=7,
                        mfc=COLOURS[source] if marker == "o" else "white",
                        label=f"R from {name}" if i == 0 else None)
        ax.text(entry["reference_nm"] + 2, y + 0.38, f"{source}", fontsize=11)
    ax.set_yticks([])
    ax.set_xlabel("Wavelength [nm]")
    ax.set_ylim(0.4, len(sources) + 0.6)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, frameon=False, fontsize=10, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def make_all(clips, results, out, data_dir):
    counting_plot(data_dir, out / "fringe_counting.png")
    counts_plot(clips, out / "fringe_counts.png")
    wavelength_plot(results, out / "wavelengths.png")
