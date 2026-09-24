# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""Recognise input images of the known blob objects and calibrate the rendering pipeline.

For an input image the known objects are rendered for the camera set-ups documented in the
original scene files (camera z = -10, -11, -13) and the pose/light given in the file name
(e.g. ``..._CamRot_y30_CamRot_x0_LighPos_x0_y-10_z-10...``).  The best silhouette match gives
object identity and camera; the integer offset of the rendered frame in the input frame and
the tone curve (monotone LUT, isotonic regression) are then estimated so that the re-rendered
anchors reproduce the input images.

Input frames: full POV-Ray frames (4:3, any resolution), or windows cropped from the 1100 x 825
frame of the original scripts (e.g. the 1078 x 617 images of coxlab/povray_blobs,
images/Blobs_TrainingRatsD1D2, cropped by ResizeBlobRatStims.m).
"""
from __future__ import annotations

import os
import re

import numpy as np

from . import presets
from . import render as R
from . import tone as tonemod
from .scene import Setup
from .stimuli import BBOX_LEVEL, bbox, is_antialiased, place, resize

CAMERA_Z = (-11.0, -10.0, -13.0)
REF_FRAME = (825, 1100)  # rows, cols of the frames rendered by the original Perl scripts


def filename_hints(path):
    """Pose / light / identity hints from Cox-lab style file names."""
    name = os.path.basename(str(path)) if path else ""
    h = {}
    m = re.search(r"CamRot_y(-?\d+(?:\.\d+)?)", name)
    if m:
        h["rot_y"] = float(m.group(1))
    m = re.search(r"CamRot_x(-?\d+(?:\.\d+)?)", name)
    if m:
        h["rot_x"] = float(m.group(1))
    m = re.search(r"LighPos_x(-?\d+(?:\.\d+)?)_y(-?\d+(?:\.\d+)?)_z(-?\d+(?:\.\d+)?)", name)
    if m:
        h["light"] = [float(m.group(i)) for i in (1, 2, 3)]
    m = re.search(r"(?:Blob_|_)(?:N|D)([12])(?:_|\b|\.)", name)
    if m:
        h["object"] = int(m.group(1))
    return h


def render_frame(img_shape):
    """Rendered frame (rows, cols) for an input image: the image itself for 4:3 frames,
    the 1100 x 825 frame for smaller windows, None otherwise."""
    H, W = int(img_shape[0]), int(img_shape[1])
    if abs(W / float(H) - 4.0 / 3.0) <= 0.02:
        return H, W
    if H <= REF_FRAME[0] and W <= REF_FRAME[1]:
        return REF_FRAME
    return None


def _iou(a, b):
    u = (a | b).sum()
    return (a & b).sum() / u if u else 0.0


def _best_offset(render_mask, img_mask, search=3):
    """Offset of the rendered frame in the input frame (bbox bottom-centre, then IoU)."""
    br, bi = bbox(render_mask.astype(np.uint8) * 255), bbox(img_mask.astype(np.uint8) * 255)
    if br is None or bi is None:
        return (0, 0), 0.0
    dr0 = bi[1] - br[1]
    dc0 = int(round(((bi[2] + bi[3]) - (br[2] + br[3])) / 2.0))
    best = ((dr0, dc0), -1.0)
    for dr in range(dr0 - search, dr0 + search + 1):
        for dc in range(dc0 - search, dc0 + search + 1):
            v = _iou(place(render_mask, (dr, dc), img_mask.shape), img_mask)
            if v > best[1]:
                best = ((dr, dc), v)
    return best


def identify_image(img, path=None, verbose=False):
    """Return the best match of `img` (grey float) to the known objects, or None."""
    frame = render_frame(img.shape)
    if frame is None:
        return None
    RH, RW = frame
    hints = filename_hints(path)
    view = (hints.get("rot_x", 0.0), hints.get("rot_y", 0.0), 0.0)
    light = hints.get("light", [0.0, -10.0, -10.0])
    q = 4 if RW >= 400 else 1
    small_mask = resize(img, 1.0 / q).astype(float) > BBOX_LEVEL
    best = None
    for which, fn in ((1, presets.object1), (2, presets.object2)):
        obj = fn(view=view)
        for cz in CAMERA_Z:
            s = Setup(width=RW, height=RH, cam_location=[0, 0, cz], light=light, antialias=False)
            lin = R.render(obj, s, RW // q, RH // q, supersample=2)
            m = lin > BBOX_LEVEL / 255.0  # object pixels are >= ambient (0.4)
            _, v = _best_offset(m, small_mask)
            if verbose:
                print("  object %d camera z=%g: IoU %.4f" % (which, cz, v))
            if best is None or v > best["iou_small"]:
                best = {"object": which, "cam_z": cz, "iou_small": v, "view": view,
                        "light": light}
    if best is None or best["iou_small"] < 0.93:
        return None
    # full-resolution calibration
    s = Setup(width=RW, height=RH, cam_location=[0, 0, best["cam_z"]], light=best["light"],
              antialias=True, aa_threshold=0.3)
    obj = (presets.object1 if best["object"] == 1 else presets.object2)(view=best["view"])
    lin = R.render(obj, s)
    shift, iou = _best_offset(lin > 0.3, img > BBOX_LEVEL)
    best.update({"shift": shift, "iou": float(iou), "frame": frame,
                 "linear": place(lin, shift, img.shape)})
    return best


def calibrate_tone(matches, images):
    """Joint monotone LUT from the aligned renders of identified images."""
    from scipy import ndimage
    xs, ys = [], []
    for m, img in zip(matches, images):
        lin = m["linear"]
        inner = ndimage.binary_erosion(lin > 0.3, iterations=3) & \
            ndimage.binary_erosion(img > BBOX_LEVEL, iterations=3)
        xs.append(lin[inner])
        ys.append(img[inner])
    x = np.concatenate(xs)
    y = np.concatenate(ys)
    lut = tonemod.estimate_lut(x, y)
    # a named curve is used when it explains the data as well as the fitted LUT
    v8 = np.clip(np.round(255 * x), 0, 255).astype(int)
    lv = np.unique(v8)
    choice, err_best = lut, np.abs(lut[v8] - y).mean()
    for name in ("zoccolan", "linear", "srgb"):
        pred = tonemod.apply_tone(x, name).astype(float)
        err = np.abs(pred - y).mean()
        if err <= err_best + 0.15:
            choice, err_best = name, err
            break
    return choice, float(err_best), lv


def _apply_frame(setup: Setup, img_shape, frame):
    setup.height, setup.width = frame
    setup.out_shape = tuple(img_shape) if tuple(img_shape) != tuple(frame) else (0, 0)


def calibrate_to_images(obj_a, obj_b, setup: Setup, img_a, img_b):
    """Offset and tone curve so that renders of known models reproduce the given images."""
    s = setup.copy()
    frame = render_frame(img_a.shape) or tuple(img_a.shape)
    _apply_frame(s, img_a.shape, frame)
    s.shift = (0, 0)
    matches = []
    for obj, img in ((obj_a, img_a), (obj_b, img_b)):
        lin = R.render(obj, s)
        shift, iou = _best_offset(lin > 0.3, img > BBOX_LEVEL)
        matches.append({"shift": shift, "iou": float(iou), "linear": place(lin, shift, img.shape)})
    tone_spec, err, _ = calibrate_tone(matches, [img_a, img_b])
    s.tone = tone_spec if isinstance(tone_spec, str) else [float(v) for v in tone_spec]
    s.shift = (int(round((matches[0]["shift"][0] + matches[1]["shift"][0]) / 2.0)),
               int(round((matches[0]["shift"][1] + matches[1]["shift"][1]) / 2.0)))
    s.antialias = is_antialiased(img_a) or is_antialiased(img_b)
    return s, {"iou_a": matches[0]["iou"], "iou_b": matches[1]["iou"], "tone_mae": err,
               "shift_a": matches[0]["shift"], "shift_b": matches[1]["shift"]}


def identify_pair(img_a, img_b, path_a=None, path_b=None, verbose=False):
    """Try to recognise both inputs as the two known objects. Returns dict or None."""
    ma = identify_image(img_a, path_a, verbose)
    mb = identify_image(img_b, path_b, verbose)
    if ma is None or mb is None or ma["object"] == mb["object"]:
        return None
    tone_spec, err, _ = calibrate_tone([ma, mb], [img_a, img_b])
    setup = presets.setup_for("provided")
    _apply_frame(setup, img_a.shape, ma["frame"])
    setup.cam_location = np.array([0.0, 0.0, ma["cam_z"]])
    setup.light = np.asarray(ma["light"], dtype=float)
    setup.tone = tone_spec if isinstance(tone_spec, str) else [float(v) for v in tone_spec]
    setup.shift = (int(round((ma["shift"][0] + mb["shift"][0]) / 2.0)),
                   int(round((ma["shift"][1] + mb["shift"][1]) / 2.0)))
    setup.antialias = is_antialiased(img_a) or is_antialiased(img_b)
    return {"setup": setup, "reversed": ma["object"] == 2, "view": ma["view"],
            "match_a": {k: v for k, v in ma.items() if k != "linear"},
            "match_b": {k: v for k, v in mb.items() if k != "linear"},
            "tone_mae": err}
