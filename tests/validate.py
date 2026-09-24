# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""Validation of blobmorph (VALIDATION.md, sections 1 to 3).

    python tests/validate.py [--images FOLDER] [--figure FILE]

--images  image bank, default Images/Blobs_TrainingRatsD1D2 (README, Image bank)
--figure  1637 x 572 px crop of Rhee et al. (2025), Fig. S4A (section 3, skipped without it)

1. built-in renderer vs POV-Ray 3.7 renders of the scene files (tests/povray_reference)
2. objects re-rendered from the scene files vs the images of the image bank
3. object sizes per morph level vs Fig. S4A
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from blobmorph import identify, morph, presets, render as R, stimuli as S, tone  # noqa: E402

BANK = os.path.join(HERE, "..", "Images", "Blobs_TrainingRatsD1D2")
NAME_ROT = "Blob_N%d_CamRot_y%d.png"
NAME_5 = "Blob_N%d_5_CamRot_y0_CamRot_x0_LighPos_x0_y-10_z-10_Size1.png"


def povray_reference():
    print("1) built-in renderer vs POV-Ray 3.7 (tests/povray_reference, camera z = -10, no AA)")
    ref = os.path.join(HERE, "povray_reference")
    s = presets.setup_for("zoccolan2009")
    s.antialias = False
    for k, obj in ((1, presets.object1()), (2, presets.object2())):
        p = os.path.join(ref, "obj%d_cam10_povray37_noAA_srgb.png" % k)
        if not os.path.isfile(p):
            print("   (missing %s)" % p)
            continue
        pov = S.load_gray(p)
        mine = tone.apply_tone(R.render(obj, s), "srgb").astype(float)
        m1, m2 = mine > 0, pov > 0
        d = np.abs(mine - pov)
        print("   object %d: differing silhouette pixels %d of %d, mean abs difference over the "
              "object %.4f grey levels" % (k, (m1 ^ m2).sum(), m2.sum(), d[m1 | m2].mean()))


def image_pairs(folder):
    pairs = []
    for rot in range(-90, 91, 15):
        pa, pb = (os.path.join(folder, NAME_ROT % (k, rot)) for k in (1, 2))
        if os.path.isfile(pa) and os.path.isfile(pb):
            pairs.append(("y%d" % rot, pa, pb))
    pa, pb = (os.path.join(folder, NAME_5 % k) for k in (1, 2))
    if os.path.isfile(pa) and os.path.isfile(pb):
        pairs.append(("N1_5, N2_5", pa, pb))
    return pairs


def image_bank(folder):
    print("2) objects re-rendered from the scene files vs the images (%s)" % os.path.abspath(folder))
    pairs = image_pairs(folder)
    if not pairs:
        print("   (no images found; README, Image bank)")
        return
    print("   %-11s %-7s %-12s %-5s %-9s | %-33s | %-33s" % (
        "images", "cam z", "shift", "AA", "tone", "object 1: MAE int/edge/all, IoU",
        "object 2: MAE int/edge/all, IoU"))
    for label, pa, pb in pairs:
        a, b = S.load_gray(pa), S.load_gray(pb)
        idp = identify.identify_pair(a, b, pa, pb)
        if idp is None:
            print("   %-11s not recognised" % label)
            continue
        s = idp["setup"]
        cols = []
        for obj, img in ((presets.object1(view=idp["view"]), a),
                         (presets.object2(view=idp["view"]), b)):
            r = S.place(tone.apply_tone(R.render(obj, s), s.tone), s.shift,
                        s.frame_shape()).astype(float)
            u = (r > 0) | (img > 0)
            inner = ndimage.binary_erosion(u, iterations=3)
            d = r - img
            iou = ((r > 40) & (img > 40)).sum() / ((r > 40) | (img > 40)).sum()
            cols.append("%5.2f %5.2f %6.3f  %.4f" % (
                np.abs(d[inner]).mean(), np.abs(d[u & ~inner]).mean(), np.abs(d).mean(), iou))
        print("   %-11s %-7g %-12s %-5s %-9s | %-33s | %-33s" % (
            label, s.cam_location[2], tuple(s.shift), s.antialias,
            s.tone if isinstance(s.tone, str) else "LUT", cols[0], cols[1]), flush=True)


def figure_levels(fig):
    print("3) object bounding boxes per level vs Fig. S4A (rows 50 to 20 deg)")
    if not fig or not os.path.isfile(fig):
        print("   (skipped: give --figure with the crop of Fig. S4A)")
        return
    a = np.asarray(Image.open(fig).convert("RGB")).astype(float).mean(-1)
    if a.shape != (572, 1637):
        print("   (skipped: pixel coordinates below refer to a 1637 x 572 px crop)")
        return
    P = a[90:477, 141:1500]  # panel of the 9 x 4 largest stimuli
    lab, _ = ndimage.label(P > 40)
    cells = {}
    for i, sl in enumerate(ndimage.find_objects(lab)):
        ys, xs = sl
        if (lab[sl] == i + 1).sum() < 100 or xs.stop - xs.start < 14:
            continue
        cells[(int(((ys.start + ys.stop) / 2) // 78), int(((xs.start + xs.stop) / 2) // 149))] = \
            (xs.stop - xs.start, ys.stop - ys.start)
    pw = np.array([[cells[(r, c)][0] for c in range(9)] for r in range(4)], float)
    ph = np.array([[cells[(r, c)][1] for c in range(9)] for r in range(4)], float)
    s = presets.setup_for("provided")
    s.antialias = False
    A, B = presets.rhee_morph_endpoints()
    sets = {"uniform t = k/8": np.linspace(0, 1, 9),
            "M-index k/106": np.array([0, 14, 27, 40, 53, 66, 79, 92, 106]) / 106.0}
    cum_file = os.environ.get("BLOBMORPH_ARC_T")
    if cum_file:
        sets["arc"] = np.array([float(x) for x in cum_file.split(",")])
    for name, ts in sets.items():
        W, H = [], []
        for t in ts:
            img = tone.apply_tone(R.render(morph.interpolate(A, B, t), s), "zoccolan")
            r0, r1, c0, c1 = S.bbox(img)
            W.append(c1 - c0 + 1)
            H.append(r1 - r0 + 1)
        W, H = np.array(W, float), np.array(H, float)
        errs = []
        for r in range(4):
            k = pw[r].mean() / W.mean()
            errs.append(np.r_[np.abs(W * k - pw[r]), np.abs(H * k - ph[r])].mean())
        print("   %-16s mean |error| %.2f px (per row %s)" % (name, np.mean(errs), np.round(errs, 2)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="python tests/validate.py")
    ap.add_argument("--images", default=BANK, help="image folder (default: image bank)")
    ap.add_argument("--figure", help="1637 x 572 px crop of Fig. S4A (Rhee et al. 2025)")
    args = ap.parse_args()
    povray_reference()
    image_bank(args.images)
    figure_levels(args.figure)
