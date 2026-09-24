# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""Post-processing of rendered morphs into stimuli of given sizes (degrees of visual angle).

* centring   : ResizeBlobRatStims_General_morphs.m (Zoccolan / Rhee) - the union bounding box
               (pixels > 40) of the two anchor images is centred in the frame; the same
               translation is applied to every morph, so relative positions are preserved;
* cropping   : common crop = union bounding box of all morph levels (+/- 2 px);
* sizes      : the crop is scaled so that its reference dimension spans `size` degrees
               (like an MWorks image stimulus with x_size/y_size in degrees);
* luminance  : grey level of a full-field screen with the same mean luminance as the screen
               showing the stimulus (Rhee et al. 2025 luminance controls, Fig. S4A).
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

BBOX_LEVEL = 40  # FindImageBoundingBox_call.m: pixels higher than 40 are object


def load_gray(path) -> np.ndarray:
    """Image file -> float grey levels (MATLAB rgb2gray weights for colour images)."""
    im = Image.open(path)
    if im.mode in ("I;16", "I;16B", "I"):
        a = np.asarray(im).astype(np.float64)
        return a * (255.0 / max(a.max(), 1.0))
    if im.mode not in ("L", "RGB"):
        im = im.convert("RGB")
    a = np.asarray(im).astype(np.float64)
    if a.ndim == 3:
        a = 0.2989 * a[..., 0] + 0.5870 * a[..., 1] + 0.1140 * a[..., 2]
    return a


def bbox(img, level=BBOX_LEVEL):
    """(row0, row1, col0, col1) inclusive, 0-based, of pixels > level (None if empty)."""
    ys, xs = np.nonzero(np.asarray(img) > level)
    if ys.size == 0:
        return None
    return int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())


def is_antialiased(img, level=BBOX_LEVEL):
    """True when the object edges contain intermediate grey levels (antialiased render)."""
    from scipy import ndimage
    img = np.asarray(img)
    obj = img > 0
    if not obj.any():
        return False
    edge = obj & ~ndimage.binary_erosion(obj)
    return bool((obj & (img <= level)).sum() > 0.05 * edge.sum())


def union_bbox(images, level=BBOX_LEVEL):
    boxes = [b for b in (bbox(im, level) for im in images) if b is not None]
    if not boxes:
        raise ValueError("no object pixels found")
    return (min(b[0] for b in boxes), max(b[1] for b in boxes),
            min(b[2] for b in boxes), max(b[3] for b in boxes))


def centring_shift(anchor_images, horizontal=True, level=BBOX_LEVEL):
    """Translation (rows, cols) that centres the anchors' union bounding box.

    Reproduces ResizeBlobRatStims_General_morphs.m (1-based MATLAB indices):
        Drow(1) = nrow - row_max ; Drow(2) = row_min ; TransRow = (Drow(1) - Drow(2)) / 2
    (the anchors of Fig. S4A, Blob_N{1,2}_5_..., were shifted by TransRow = -22).
    """
    r0, r1, c0, c1 = union_bbox(anchor_images, level)
    nrow, ncol = np.asarray(anchor_images[0]).shape[:2]
    trans_row = ((nrow - (r1 + 1)) - (r0 + 1)) / 2.0
    trans_col = ((ncol - (c1 + 1)) - (c0 + 1)) / 2.0 if horizontal else 0.0
    return int(round(trans_row)), int(round(trans_col))


def place(img, shift, shape=None):
    """Copy `img` into a black frame of size `shape` (default: same size), pixel (r, c)
    going to (r + shift[0], c + shift[1]). Used to crop a rendered frame to the window of
    an input image, or to translate it (MATLAB imdilate(img, translate(strel(1), v)))."""
    dr, dc = int(shift[0]), int(shift[1])
    h, w = img.shape[:2]
    shape = (h, w) if shape is None else (int(shape[0]), int(shape[1]))
    out = np.zeros(shape + img.shape[2:], dtype=img.dtype)
    r0, c0 = max(0, dr), max(0, dc)
    r1, c1 = min(shape[0], h + dr), min(shape[1], w + dc)
    if r1 > r0 and c1 > c0:
        out[r0:r1, c0:c1] = img[r0 - dr:r1 - dr, c0 - dc:c1 - dc]
    return out


def translate(img, shift):
    """Integer translation with zero (black) fill, same image size."""
    return place(img, shift)


def crop_box(images, margin=2, level=BBOX_LEVEL):
    """Common crop (row0, row1, col0, col1) exclusive-end, = union bbox +/- margin."""
    r0, r1, c0, c1 = union_bbox(images, level)
    h, w = np.asarray(images[0]).shape[:2]
    return max(0, r0 - margin), min(h, r1 + 1 + margin), max(0, c0 - margin), min(w, c1 + 1 + margin)


# ------------------------------------------------------------------------------------------
# degrees <-> pixels
# ------------------------------------------------------------------------------------------
class Display:
    """Display geometry used to convert degrees of visual angle to pixels.

    Either give px_per_deg directly, or the screen width (cm), its horizontal resolution
    (px) and the viewing distance (cm).  deg_mode:
      'mworks'  : linear mapping, the whole screen width spans 2*atan(w/2d) degrees
                  (how MWorks defines stimulus sizes in degrees)
      'tangent' : exact visual angle of a stimulus centred on the line of sight:
                  size_px = 2 d tan(size/2) * px_per_cm
      'linear'  : small-angle approximation, size_px = size * pi/180 * d * px_per_cm
    """

    def __init__(self, px_per_deg=None, screen_px=(1920, 1080), screen_cm=None,
                 distance_cm=None, deg_mode="mworks"):
        self.screen_px = (int(screen_px[0]), int(screen_px[1]))
        self.screen_cm = screen_cm
        self.distance_cm = distance_cm
        self.deg_mode = deg_mode
        if px_per_deg is None and (screen_cm is None or distance_cm is None):
            px_per_deg = 16.05  # Rhee et al. (2025) imaging display (analyze2p sim_utils.py)
        self._ppd = px_per_deg

    def px_per_cm(self):
        return self.screen_px[0] / float(self.screen_cm)

    def size_px(self, size_deg):
        if self._ppd is not None:
            return size_deg * self._ppd
        d, ppc = float(self.distance_cm), self.px_per_cm()
        if self.deg_mode == "mworks":
            half_deg = math.degrees(math.atan(self.screen_cm / 2.0 / d))
            return size_deg * (self.screen_px[0] / 2.0) / half_deg
        if self.deg_mode == "tangent":
            return 2.0 * d * math.tan(math.radians(size_deg) / 2.0) * ppc
        if self.deg_mode == "linear":
            return math.radians(size_deg) * d * ppc
        raise ValueError("unknown deg_mode %r" % self.deg_mode)

    def pos_px(self, pos_deg):
        """Screen position (x right, y up, degrees from centre) -> pixel (col, row) of centre."""
        cx = self.screen_px[0] / 2.0 + math.copysign(self.size_px(abs(pos_deg[0])), pos_deg[0])
        cy = self.screen_px[1] / 2.0 - math.copysign(self.size_px(abs(pos_deg[1])), pos_deg[1])
        return cx, cy

    def describe(self):
        return {"px_per_deg": self._ppd, "screen_px": list(self.screen_px),
                "screen_cm": self.screen_cm, "distance_cm": self.distance_cm,
                "deg_mode": self.deg_mode, "px_per_deg_effective_at_10deg": self.size_px(10.0) / 10.0}


def reference_length(crop_img_shape, ref, obj_bbox=None):
    h, w = crop_img_shape[:2]
    if ref == "crop_max":
        return max(h, w)
    if ref == "crop_width":
        return w
    if ref == "crop_height":
        return h
    if ref == "object_max":
        r0, r1, c0, c1 = obj_bbox
        return max(r1 - r0 + 1, c1 - c0 + 1)
    raise ValueError("unknown size reference %r" % ref)


def resize(img, scale):
    """High quality resampling of a grey image by `scale` (box/area filter for shrinking,
    bicubic for enlarging), on float values; returns uint8."""
    h, w = img.shape[:2]
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    im = Image.fromarray(np.ascontiguousarray(img, dtype=np.float32))  # mode 'F'
    out = np.asarray(im.resize((nw, nh), Image.BOX if scale < 1 else Image.BICUBIC))
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def compose_screen(stim, display: Display, pos_deg=(0.0, 0.0), background=0):
    """Paste a stimulus on a full screen (background grey level), centred at pos_deg."""
    W, H = display.screen_px
    screen = np.full((H, W), background, dtype=np.uint8)
    cx, cy = display.pos_px(pos_deg)
    h, w = stim.shape
    r0 = int(round(cy - h / 2.0))
    c0 = int(round(cx - w / 2.0))
    rs0, cs0 = max(0, -r0), max(0, -c0)
    rs1, cs1 = min(h, H - r0), min(w, W - c0)
    if rs1 > rs0 and cs1 > cs0:
        screen[r0 + rs0:r0 + rs1, c0 + cs0:c0 + cs1] = stim[rs0:rs1, cs0:cs1]
    return screen


def mean_luminance_level(img, display_gamma=2.2):
    """Grey level whose full-field luminance equals the mean luminance of `img`.

    With display_gamma = 1 this is the plain mean pixel value (linearised display)."""
    x = np.asarray(img, dtype=np.float64) / 255.0
    lum = np.mean(np.power(x, display_gamma))
    return 255.0 * lum ** (1.0 / display_gamma)
