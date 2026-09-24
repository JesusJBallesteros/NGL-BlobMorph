# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""Tone curves: from POV-Ray's linear intensity to the 8-bit stimulus pixel values.

* ``linear``    - POV-Ray 3.6 (or 3.7 with ``#version 3.6``): value = round(255 * I)
* ``srgb``      - POV-Ray 3.7 default (no #version): sRGB-encoded output
* ``gamma:G``   - value = 255 * I^(1/G)
* ``zoccolan``  - the curve measured on the 1100 x 825 anchors of Rhee et al. (2025), Fig. S4A
                  (Blob_N{1,2}_5_CamRot_y0_CamRot_x0_LighPos_x0_y-10_z-10_Size1.png), also
                  found in coxlab/povray_blobs images/Blobs_TrainingRatsD1D2:
                  POV-Ray linear output (8 bit) followed by a colour-managed RGB -> gray
                  conversion (~ decode as sRGB, re-encode with gamma 1.72).  Values
                  102..255 are the measured medians (+-1 grey level); lower values
                  (antialiased edges) use the fitted parametric curve.
* a path to a .npy/.json/.csv/.txt file with 256 values (custom LUT on 8-bit linear values)
"""
from __future__ import annotations

import json
import os

import numpy as np

ZOCCOLAN_LUT = np.array([
    0, 2, 4, 4, 5, 6, 7, 7, 8, 8, 9, 9, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 16, 16, 17, 18,
    18, 19, 19, 20, 21, 21, 22, 23, 23, 24, 25, 25, 26, 27, 28, 28, 29, 30, 30, 31, 32, 33, 33,
    34, 35, 36, 36, 37, 38, 39, 40, 40, 41, 42, 43, 44, 44, 45, 46, 47, 48, 49, 49, 50, 51, 52,
    53, 54, 54, 55, 56, 57, 58, 59, 60, 61, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 71, 72,
    73, 74, 75, 76, 77, 78, 79, 80, 80, 81, 82, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93,
    95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113,
    114, 115, 116, 117, 118, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132,
    134, 135, 136, 137, 138, 139, 140, 141, 142, 144, 145, 146, 147, 148, 149, 150, 152, 153,
    154, 155, 156, 157, 158, 159, 161, 162, 163, 164, 165, 166, 168, 169, 170, 171, 172, 174,
    175, 176, 177, 178, 179, 181, 182, 183, 184, 185, 186, 188, 189, 190, 191, 193, 194, 195,
    196, 198, 199, 200, 201, 202, 204, 205, 206, 207, 209, 210, 211, 212, 213, 215, 216, 217,
    219, 220, 221, 222, 224, 225, 226, 227, 228, 230, 231, 232, 233, 235, 236, 237, 239, 240,
    241, 243, 244, 245, 247, 248, 249, 250, 252, 253, 254], dtype=float)


def _srgb_encode(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def load_lut(spec):
    """Return a 256-entry LUT (float) for LUT-type tone specs, else None."""
    if isinstance(spec, (list, tuple, np.ndarray)):
        lut = np.asarray(spec, dtype=float).ravel()
    elif spec == "zoccolan":
        lut = ZOCCOLAN_LUT
    elif isinstance(spec, str) and os.path.isfile(spec):
        if spec.lower().endswith(".npy"):
            lut = np.load(spec).astype(float).ravel()
        elif spec.lower().endswith(".json"):
            with open(spec, encoding="utf-8") as f:
                lut = np.asarray(json.load(f), dtype=float).ravel()
        else:
            lut = np.loadtxt(spec, delimiter="," if spec.lower().endswith(".csv") else None).ravel()
    else:
        return None
    if lut.size != 256:
        raise ValueError("a tone LUT must have 256 entries")
    return lut


def apply_tone(linear, spec="linear") -> np.ndarray:
    """Linear intensity (float, POV-Ray units) -> uint8 image."""
    x = np.clip(np.asarray(linear, dtype=float), 0.0, 1.0)
    lut = load_lut(spec)
    if lut is not None:
        v8 = np.round(255.0 * x).astype(np.int64)
        return np.clip(np.round(lut[v8]), 0, 255).astype(np.uint8)
    if spec in (None, "linear"):
        out = 255.0 * x
    elif spec == "srgb":
        out = 255.0 * _srgb_encode(x)
    elif isinstance(spec, str) and spec.startswith("gamma:"):
        g = float(spec.split(":", 1)[1])
        out = 255.0 * np.power(x, 1.0 / g)
    else:
        raise ValueError(f"unknown tone curve {spec!r}")
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def tone_function(spec):
    """Continuous version (float -> float in 0..255), used for fitting."""
    lut = load_lut(spec)
    if lut is not None:
        grid = np.arange(256) / 255.0
        return lambda x: np.interp(np.clip(x, 0, 1), grid, lut)
    return lambda x: apply_tone_float(x, spec)


def apply_tone_float(x, spec):
    x = np.clip(np.asarray(x, dtype=float), 0.0, 1.0)
    if spec in (None, "linear"):
        return 255.0 * x
    if spec == "srgb":
        return 255.0 * _srgb_encode(x)
    if isinstance(spec, str) and spec.startswith("gamma:"):
        return 255.0 * np.power(x, 1.0 / float(spec.split(":", 1)[1]))
    raise ValueError(f"unknown tone curve {spec!r}")


def estimate_lut(linear_values, target_values):
    """Monotone LUT (256) mapping 8-bit linear render values to observed pixel values.

    Pooled-adjacent-violators isotonic regression on the median target of each level;
    missing levels are interpolated, and the curve is pinned at 0 -> 0.
    """
    v = np.clip(np.round(255.0 * np.asarray(linear_values, float)), 0, 255).astype(int).ravel()
    y = np.asarray(target_values, dtype=float).ravel()
    lv, med, wt = [], [], []
    for level in np.unique(v):
        sel = y[v == level]
        if sel.size >= 3:
            lv.append(level)
            med.append(np.median(sel))
            wt.append(sel.size)
    lv = np.array([0] + lv)
    med = np.array([0.0] + med)
    wt = np.array([1e6] + wt, dtype=float)
    # isotonic regression (PAVA)
    blocks = [[m, w, 1] for m, w in zip(med, wt)]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0]:
            m0, w0, n0 = blocks[i]
            m1, w1, n1 = blocks.pop(i + 1)
            blocks[i] = [(m0 * w0 + m1 * w1) / (w0 + w1), w0 + w1, n0 + n1]
            i = max(i - 1, 0)
        else:
            i += 1
    fit = np.concatenate([[b[0]] * b[2] for b in blocks])
    lut = np.interp(np.arange(256), lv, fit)
    if lv.max() < 255:  # extrapolate the top linearly with the last slope
        top = lv.max()
        slope = (fit[-1] - fit[max(len(fit) - 6, 0)]) / max(top - lv[max(len(lv) - 6, 0)], 1)
        lut[top:] = fit[-1] + slope * (np.arange(top, 256) - top)
    return np.clip(lut, 0, 255)
