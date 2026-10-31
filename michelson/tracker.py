"""Read brightness time series from Tracker (.trk / .trz) files.

Tracker (https://physlets.org/tracker/) stores the colour measured by an "RGB region" track in
every video frame inside its XML project file, as rows of {R, G, B, pixel count}.
"""
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np


def read_project(path):
    """Return the XML text of a Tracker project (.trk) or a Tracker zip bundle (.trz)."""
    path = Path(path)
    if path.suffix == ".trz":
        with zipfile.ZipFile(path) as bundle:
            name = next(n for n in bundle.namelist() if n.endswith(".trk"))
            return bundle.read(name).decode("utf-8")
    return path.read_text(encoding="utf-8")


def rgb_regions(xml_text):
    """All RGB-region tracks in a project, as {track name: array of shape (frames, 4)}."""
    regions = {}
    for obj in ET.fromstring(xml_text).iter("object"):
        if not obj.get("class", "").endswith(".RGBRegion"):
            continue
        name = obj.findtext("property[@name='name']")
        for prop in obj.iter("property"):
            if prop.get("name") == "rgb":
                rows = re.findall(r"\{([^{}]*)\}", prop.findtext("property[@name='array']"))
                regions[name] = np.array([[float(v) for v in row.split(",")] for row in rows if row.strip()])
    return regions


def luma(rgb):
    """Perceived brightness of each frame (Rec. 601 weights, as used by Tracker)."""
    return 0.299 * rgb[:, 0] + 0.587 * rgb[:, 1] + 0.114 * rgb[:, 2]


def frame_rate(xml_text, default=30.0):
    """Video frame rate if stored in the project, otherwise the phone camera's 30 fps."""
    match = re.search(r'name="frame_rate"[^>]*>([\d.]+)<', xml_text)
    return float(match.group(1)) if match else default


def brightness(path, region="region A"):
    """Brightness time series of one RGB region in a Tracker file."""
    regions = rgb_regions(read_project(path))
    if region not in regions:
        raise KeyError(f"{path} has no track called {region!r} (found: {', '.join(regions)})")
    return luma(regions[region])
