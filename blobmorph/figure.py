# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""Morph-matrix figure in the style of Rhee et al. (2025) Fig. S4A / Fig. 1A."""
from __future__ import annotations

import numpy as np


def compose_panel(stims, sizes, levels, fig_scale, cell_aspect=1.9, pad=1.04):
    """Black panel with stims[i][j] (size i, level j) centred in a grid.

    Rows are ordered with the largest size on top.  Returns (panel, cell_w, cell_h, row_order).
    """
    from .stimuli import resize
    order = list(np.argsort(sizes)[::-1])
    scaled = [[resize(stims[i][j], fig_scale) for j in range(len(levels))] for i in range(len(sizes))]
    max_h = max(im.shape[0] for row in scaled for im in row)
    max_w = max(im.shape[1] for row in scaled for im in row)
    cell_h = int(np.ceil(max_h * pad))
    cell_w = int(max(np.ceil(max_w * 1.08), np.ceil(cell_h * cell_aspect)))
    panel = np.zeros((cell_h * len(sizes), cell_w * len(levels)), dtype=np.uint8)
    for r, i in enumerate(order):
        for j in range(len(levels)):
            im = scaled[i][j]
            h, w = im.shape
            r0 = r * cell_h + (cell_h - h) // 2
            c0 = j * cell_w + (cell_w - w) // 2
            panel[r0:r0 + h, c0:c0 + w] = np.maximum(panel[r0:r0 + h, c0:c0 + w], im)
    return panel, cell_w, cell_h, order


def _tick_levels(levels):
    lv = np.asarray(levels, dtype=float)
    quarters = [j for j, v in enumerate(lv) if abs(v / 25.0 - round(v / 25.0)) < 1e-6]
    if len(lv) > 6 and len(quarters) >= 3:
        return quarters
    if len(lv) <= 11:
        return list(range(len(lv)))
    step = int(np.ceil(len(lv) / 6.0))
    idx = list(range(0, len(lv), step))
    if idx[-1] != len(lv) - 1:
        idx.append(len(lv) - 1)
    return idx


def matrix_figure(stims, sizes, levels, out_png, out_pdf=None, fig_scale=None,
                  luminance=None, title=None, cell_aspect=1.9, target_cell_h=170, dpi=200):
    """Draw and save the morph matrix. `luminance`: grey level per size (or None)."""
    from matplotlib.figure import Figure  # no pyplot: the backend of the caller is not changed
    from matplotlib.patches import Rectangle

    if fig_scale is None:
        max_h = max(im.shape[0] for row in stims for im in row)
        fig_scale = min(1.0, target_cell_h / float(max_h))
    panel, cell_w, cell_h, order = compose_panel(stims, sizes, levels, fig_scale, cell_aspect)
    H, W = panel.shape
    lum_w = cell_h * 0.95 if luminance is not None else 0
    gap = cell_h * 0.25 if luminance is not None else 0
    total_w = W + gap + lum_w
    inch_per_px = 11.0 / max(total_w, 1)
    fig_w = total_w * inch_per_px + 2.0
    fig_h = H * inch_per_px + 1.6
    fig = Figure(figsize=(fig_w, fig_h))
    left, bottom = 1.1 / fig_w, 1.0 / fig_h
    ax = fig.add_axes([left, bottom, W * inch_per_px / fig_w, H * inch_per_px / fig_h])
    ax.imshow(panel, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
    xt = _tick_levels(levels)
    ax.set_xticks([(j + 0.5) * cell_w for j in xt])
    ax.set_xticklabels(["%g" % round(levels[j], 1) for j in xt], fontsize=12)
    ax.set_yticks([(r + 0.5) * cell_h for r in range(len(sizes))])
    ax.set_yticklabels(["%g" % sizes[i] for i in order], fontsize=12)
    ax.set_xlabel("morph level (%)", fontsize=14)
    ax.set_ylabel("size (deg.)", fontsize=14)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    if title:
        ax.set_title(title, fontsize=13)
    if luminance is not None:
        axl = fig.add_axes([(left * fig_w + (W + gap) * inch_per_px) / fig_w, bottom,
                            lum_w * inch_per_px / fig_w, H * inch_per_px / fig_h])
        axl.set_xlim(0, 1)
        axl.set_ylim(len(sizes), 0)
        for r, i in enumerate(order):
            g = float(luminance[i]) / 255.0
            axl.add_patch(Rectangle((0.04, r + 0.04), 0.92, 0.92, facecolor=(g, g, g),
                                    edgecolor="black", linewidth=2))
        axl.set_xticks([])
        axl.set_yticks([])
        for s in axl.spines.values():
            s.set_visible(False)
        axl.yaxis.set_label_position("right")
        axl.set_ylabel("luminance (FF)", fontsize=14, rotation=90, labelpad=8)
    fig.savefig(out_png, dpi=dpi, facecolor="white")
    if out_pdf:
        fig.savefig(out_pdf, facecolor="white")
    return panel


def distance_figure(ts_dense, cum, t_levels, levels_pct, chords, out_png, title=None):
    """Cumulative pixel distance along the continuum + distances between chosen morphs."""
    from matplotlib.figure import Figure
    fig = Figure(figsize=(12, 4.2))
    a1, a2 = fig.subplots(1, 2)
    if ts_dense is not None and cum is not None:
        a1.plot(np.asarray(ts_dense), np.asarray(cum) / max(cum[-1], 1e-12), "k-", lw=1.5,
                label="dense continuum")
        a1.plot(t_levels, np.interp(t_levels, ts_dense, np.asarray(cum) / max(cum[-1], 1e-12)),
                "o", color="tab:red", label="selected levels")
    else:
        # no dense continuum ('uniform' sampling): distances between the selected levels
        c = np.r_[0.0, np.cumsum(chords)]
        a1.plot([0, 1], [0, 1], ":", color="0.5", lw=1, label="equal distance per level step")
        a1.plot(t_levels, c / max(c[-1], 1e-12), "o-", color="tab:red", lw=1,
                label="selected levels")
    a1.set_ylabel("cumulative Euclidean distance (normalised)")
    a1.legend(frameon=False, loc="upper left")
    a1.set_xlabel("morph parameter t (0 = A, 1 = B)")
    a1.set_title("pixel-space distance along the morph")
    a2.bar(np.arange(len(chords)), chords, color="0.5")
    a2.set_xticks(np.arange(len(chords)))
    a2.set_xticklabels(["%g-%g" % (round(levels_pct[k], 1), round(levels_pct[k + 1], 1))
                        for k in range(len(chords))], rotation=45, fontsize=8)
    a2.set_ylabel("Euclidean distance between successive morphs")
    a2.set_title("check: successive sampled morphs")
    if title:
        fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
