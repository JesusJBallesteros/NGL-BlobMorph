# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""Known stimuli: the two objects of Zoccolan et al. (2009) used by Rhee et al. (2025).

Sources (read on 2026-09-23):
  * github.com/coxlab/povray_blobs  code/Blobs_RatsD1D2/StimBlob_call_{1,2}.pov,
    StimBlob_lighting_new_call_{1,2}.pov and Script_StimBlob*.pl (object pose/position,
    camera, light, 1100 x 825 frames, antialiasing);
  * github.com/julianarhee/morph-pov  make_pov_morphs.py (the morph continuum A -> B),
    utils/euclid.py (equal Euclidean-distance sampling),
    matlab/ResizeBlobRatStims_General_morphs.m (centering / cropping).
"""
from __future__ import annotations

import numpy as np

from .scene import BlobObject, Component, Setup


def _base_a():
    return Component(name="base (sfera)", radius=0.8, strength=1.0,
                     translate=[0, -0.4, 0.5], scale=[1, 1, 1], rotate=[0, 0, 0])


def _base_b():
    return Component(name="base (sfera)", radius=0.8, strength=1.0,
                     translate=[0, -0.2, 0.7], scale=[0.8, 1.4, 0.8], rotate=[20, 0, 0])


def _head_disc(strength=1.0, zscale=1.8):
    return Component(name="head disc (lenticchia)", radius=0.8, strength=strength,
                     translate=[0, 0, -0.5], scale=[1.8, 0.6, zscale], rotate=[30, 0, 0])


def _ear(side, strength=1.0):
    return Component(name="ear %s (orecchia)" % side, radius=0.8, strength=strength,
                     translate=[0, 0, -0.5], scale=[0.6, 0.6, 2.0],
                     rotate=[40, 0, 55 if side == "left" else -55])


def _nose():
    return Component(name="nose (capsula)", radius=0.8, strength=1.0,
                     translate=[0, 0, -0.5], scale=[0.5, 0.5, 1.0], rotate=[-45, 0, 0])


def _null(name):
    # make_pov_morphs.py shrinks the nose to radius 0 and all its transforms to 0
    return Component(name=name, radius=0.0, strength=1.0, translate=[0, 0, 0],
                     scale=[0, 0, 0], rotate=[0, 0, 0])


def object1(view=(0, 0, 0)) -> BlobObject:
    """Object 1 / 'A' / 'N1' / 'D1' (StimBlob_call_1.pov)."""
    return BlobObject(name="Zoccolan2009_object1", threshold=0.2,
                      components=[_base_a(), _head_disc(), _nose()],
                      rotate=view, translate=[0, -0.18, 5], scale=[0, 1.02, 0])


def object2(view=(0, 0, 0)) -> BlobObject:
    """Object 2 / 'B' / 'N2' / 'D2' (StimBlob_call_2.pov)."""
    return BlobObject(name="Zoccolan2009_object2", threshold=0.2,
                      components=[_base_b(), _ear("left"), _ear("right")],
                      rotate=view, translate=[0, 0, 6], scale=[0, 0, 0])


def rhee_morph_endpoints(view=(0, 0, 0)):
    """Extended objects A and B such that linear interpolation of *all* their numbers
    reproduces make_pov_morphs.py exactly (strengthA = t, strengthB = 1 - t, linmap steps):

      base      : A-base -> B-base (translate, scale, rotate interpolated)
      head disc : strength 1 -> 0, z-scale 1.8 -> 0.9  ("scale5")
      left ear  : strength 0 -> 1
      right ear : strength 0 -> 1
      nose      : radius .8 -> 0, translate/scale/rotate -> 0
      object    : translate <0,-0.18,5> -> <0,0,6>, scale <1,1.02,1> -> <1,1,1>
    """
    a = BlobObject(name="morphA", threshold=0.2,
                   components=[_base_a(), _head_disc(1.0, 1.8), _ear("left", 0.0),
                               _ear("right", 0.0), _nose()],
                   rotate=view, translate=[0, -0.18, 5], scale=[1, 1.02, 1])
    b = BlobObject(name="morphB", threshold=0.2,
                   components=[_base_b(), _head_disc(0.0, 0.9), _ear("left", 1.0),
                               _ear("right", 1.0), _null("nose (capsula)")],
                   rotate=view, translate=[0, 0, 6], scale=[1, 1, 1])
    return a, b


# ------------------------------------------------------------------------------------------
# Rendering set-ups
# ------------------------------------------------------------------------------------------
def setup_for(name: str = "provided") -> Setup:
    """Camera / light / tone variants documented in the original files.

    provided : matches the anchors of Fig. S4A, Blob_N{1,2}_5_..._Size1.png (camera z=-11,
               antialiased, 'zoccolan' tone curve; the images are then centred vertically)
    zoccolan2009 : StimBlob_call_*.pov as in the 2009 paper (camera z=-10, linear output)
    rhee2025 : make_pov_morphs.py (camera z=-10, POV-Ray 3.7 default sRGB output, no AA)
    """
    s = Setup()
    # (Antialias_Threshold 0.0 was used by the Perl scripts; 0.3 gives the same result
    #  to within 0.01 grey levels here and is ~7x faster.)
    if name == "provided":
        s.cam_location = np.array([0.0, 0.0, -11.0])
        s.tone = "zoccolan"
        s.antialias = True
        s.aa_threshold = 0.3
    elif name == "zoccolan2009":
        s.cam_location = np.array([0.0, 0.0, -10.0])
        s.tone = "linear"
        s.antialias = True
        s.aa_threshold = 0.3
    elif name == "rhee2025":
        s.cam_location = np.array([0.0, 0.0, -10.0])
        s.tone = "srgb"
        s.antialias = False
    else:
        raise ValueError("unknown setup %r" % name)
    return s


PRESETS = {
    "zoccolan2009": {
        "objects": (object1, object2),
        "endpoints": rhee_morph_endpoints,
        "description": "Zoccolan et al. 2009 objects 1 & 2 with the morph plan of "
                       "Rhee et al. 2025 (julianarhee/morph-pov/make_pov_morphs.py)",
    }
}
