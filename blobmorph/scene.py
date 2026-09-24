# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""Scene description compatible with the POV-Ray files used for the rat "blob" objects.

The stimuli of Zoccolan et al. (2009, PNAS) and Rhee et al. (2025, Cell Reports) are
POV-Ray ``blob`` objects: a sum of spherical density fields, each one individually
translated / scaled / rotated (so each component is an ellipsoid), rendered in white
with a single point light on a black background.  This module stores exactly those
parameters, reproduces POV-Ray's transform conventions, and can read/write the subset
of the POV-Ray scene language used by the original scripts
(coxlab/povray_blobs: StimBlob_call_*.pov, julianarhee/morph-pov: make_pov_morphs.py).
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import List, Sequence, Tuple

import numpy as np

EPS_SCALE = 1e-10  # POV-Ray replaces (near) zero scale factors by 1


# ----------------------------------------------------------------------------------------
# POV-Ray transform conventions
# ----------------------------------------------------------------------------------------
def pov_rotation(angles_deg: Sequence[float]) -> np.ndarray:
    """Matrix (acting on column vectors) equivalent to POV-Ray's ``rotate <ax, ay, az>``.

    POV-Ray rotates about x first, then y, then z, using row vectors and a left-handed
    frame.  Transposing its matrices gives the usual column-vector form R = Rz @ Ry @ Rx.
    """
    ax, ay, az = np.deg2rad(np.asarray(angles_deg, dtype=float))
    cx, sx = np.cos(ax), np.sin(ax)
    cy, sy = np.cos(ay), np.sin(ay)
    cz, sz = np.cos(az), np.sin(az)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rz @ ry @ rx


def pov_scale(v) -> np.ndarray:
    v = np.broadcast_to(np.asarray(v, dtype=float), (3,)).copy()
    v[np.abs(v) < EPS_SCALE] = 1.0  # POV-Ray: "scale value of 0 changed to 1"
    return v


def affine_from_ops(ops: Sequence[Tuple[str, Sequence[float]]]) -> Tuple[np.ndarray, np.ndarray]:
    """Compose a POV-Ray transform list into p' = M @ p + b (ops applied in order)."""
    m = np.eye(3)
    b = np.zeros(3)
    for kind, val in ops:
        if kind == "translate":
            b = b + np.asarray(val, dtype=float)
        elif kind == "scale":
            s = pov_scale(val)
            m = s[:, None] * m
            b = s * b
        elif kind == "rotate":
            r = pov_rotation(val)
            m = r @ m
            b = r @ b
        elif kind == "matrix":  # 3x3 + translation given as 12 numbers (POV-Ray order)
            v = np.asarray(val, dtype=float).reshape(4, 3)
            r = v[:3, :].T
            m = r @ m
            b = r @ b + v[3]
        else:
            raise ValueError(f"unknown transform {kind!r}")
    return m, b


# ----------------------------------------------------------------------------------------
# Scene objects
# ----------------------------------------------------------------------------------------
@dataclass
class Component:
    """One blob component: ``sphere { <0,0,0>, radius, strength  translate T scale S rotate R }``."""

    radius: float = 0.8
    strength: float = 1.0
    translate: np.ndarray = field(default_factory=lambda: np.zeros(3))
    scale: np.ndarray = field(default_factory=lambda: np.ones(3))
    rotate: np.ndarray = field(default_factory=lambda: np.zeros(3))
    center: np.ndarray = field(default_factory=lambda: np.zeros(3))
    name: str = ""

    def __post_init__(self):
        for k in ("translate", "scale", "rotate", "center"):
            setattr(self, k, np.asarray(getattr(self, k), dtype=float).reshape(3))
        self.radius = float(self.radius)
        self.strength = float(self.strength)

    def ops(self):
        return [("translate", self.translate), ("scale", self.scale), ("rotate", self.rotate)]

    def to_dict(self):
        return {"name": self.name, "radius": self.radius, "strength": self.strength,
                "translate": self.translate.tolist(), "scale": self.scale.tolist(),
                "rotate": self.rotate.tolist(), "center": self.center.tolist()}

    @staticmethod
    def from_dict(d):
        return Component(radius=d.get("radius", 0.8), strength=d.get("strength", 1.0),
                         translate=d.get("translate", [0, 0, 0]), scale=d.get("scale", [1, 1, 1]),
                         rotate=d.get("rotate", [0, 0, 0]), center=d.get("center", [0, 0, 0]),
                         name=d.get("name", ""))


@dataclass
class BlobObject:
    """A POV-Ray blob plus the object-level transform (``rotate``, ``translate``, ``scale``)."""

    components: List[Component]
    threshold: float = 0.2
    rotate: np.ndarray = field(default_factory=lambda: np.zeros(3))
    translate: np.ndarray = field(default_factory=lambda: np.zeros(3))
    scale: np.ndarray = field(default_factory=lambda: np.ones(3))
    ambient: float = 0.4
    diffuse: float = 0.6
    name: str = ""

    def __post_init__(self):
        for k in ("rotate", "translate", "scale"):
            setattr(self, k, np.asarray(getattr(self, k), dtype=float).reshape(3))

    def object_ops(self):
        return [("rotate", self.rotate), ("translate", self.translate), ("scale", self.scale)]

    def copy(self) -> "BlobObject":
        return copy.deepcopy(self)

    def component_affines(self):
        """For each component: (Winv, winv) mapping scene points to its unit-sphere frame."""
        mo, bo = affine_from_ops(self.object_ops())
        out = []
        for c in self.components:
            mc, bc = affine_from_ops(c.ops())
            m = mo @ mc
            b = mo @ bc + bo
            minv = np.linalg.inv(m)
            out.append((minv, -minv @ b))
        return out

    def to_dict(self):
        return {"name": self.name, "threshold": self.threshold,
                "rotate": self.rotate.tolist(), "translate": self.translate.tolist(),
                "scale": self.scale.tolist(), "ambient": self.ambient, "diffuse": self.diffuse,
                "components": [c.to_dict() for c in self.components]}

    @staticmethod
    def from_dict(d):
        return BlobObject(components=[Component.from_dict(c) for c in d["components"]],
                          threshold=d.get("threshold", 0.2), rotate=d.get("rotate", [0, 0, 0]),
                          translate=d.get("translate", [0, 0, 0]), scale=d.get("scale", [1, 1, 1]),
                          ambient=d.get("ambient", 0.4), diffuse=d.get("diffuse", 0.6),
                          name=d.get("name", ""))


@dataclass
class Setup:
    """Camera, light and image format (defaults = the scripts of Zoccolan et al. 2009)."""

    width: int = 1100
    height: int = 825
    cam_location: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, -10.0]))
    cam_look_at: np.ndarray = field(default_factory=lambda: np.zeros(3))
    cam_angle: float = 15.0
    cam_right: float = 1.33  # POV-Ray default right vector <1.33,0,0>
    cam_up: float = 1.0
    light: np.ndarray = field(default_factory=lambda: np.array([0.0, -10.0, -10.0]))
    shadows: bool = True
    antialias: bool = True
    aa_threshold: float = 0.0   # POV-Ray Antialias_Threshold (sum over RGB channels)
    aa_depth: int = 3           # POV-Ray Antialias_Depth -> depth x depth sub-samples
    tone: str = "linear"        # see tone.py
    shift: Tuple[int, int] = (0, 0)  # position of the rendered frame in the output frame
                                     # (rows, cols), e.g. (-22, 0)
    out_shape: Tuple[int, int] = (0, 0)  # output frame (rows, cols); (0, 0): rendered size

    def __post_init__(self):
        for k in ("cam_location", "cam_look_at", "light"):
            setattr(self, k, np.asarray(getattr(self, k), dtype=float).reshape(3))
        self.shift = (int(self.shift[0]), int(self.shift[1]))
        self.out_shape = (int(self.out_shape[0]), int(self.out_shape[1]))

    def frame_shape(self):
        """Size (rows, cols) of the output frames."""
        if self.out_shape[0] > 0 and self.out_shape[1] > 0:
            return self.out_shape
        return (int(self.height), int(self.width))

    def copy(self) -> "Setup":
        return copy.deepcopy(self)

    def to_dict(self):
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        for k, v in d.items():
            if isinstance(v, np.ndarray):
                d[k] = v.tolist()
        d["shift"] = list(self.shift)
        d["out_shape"] = list(self.out_shape)
        return d

    @staticmethod
    def from_dict(d):
        s = Setup()
        for k, v in d.items():
            if k in s.__dataclass_fields__:
                setattr(s, k, v)
        s.__post_init__()
        return s


# ----------------------------------------------------------------------------------------
# JSON helpers
# ----------------------------------------------------------------------------------------
def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def load_object(path, declared=None) -> BlobObject:
    """Load a blob object from .json (this toolbox) or .pov (POV-Ray subset).

    `declared`: values of identifiers set on the POV-Ray command line (Declare=name=value),
    e.g. {"obj_pos_z": 6, "cam_rot_y": 0} for the Cox-lab StimBlob_lighting_new_call files."""
    path = str(path)
    if path.lower().endswith(".pov") or path.lower().endswith(".inc"):
        with open(path, encoding="utf-8", errors="replace") as f:
            return parse_pov(f.read(), declared)[0]
    with open(path, encoding="utf-8") as f:
        return BlobObject.from_dict(json.load(f))


def load_setup(path):
    """Rendering set-up stored in a .json model (fitted models), or None."""
    path = str(path)
    if not path.lower().endswith(".json"):
        return None
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return Setup.from_dict(d["setup"]) if isinstance(d.get("setup"), dict) else None


# ----------------------------------------------------------------------------------------
# POV-Ray export
# ----------------------------------------------------------------------------------------
def _vec(v):
    return "<%s>" % ", ".join("%.10g" % float(x) for x in v)


def to_pov(obj: BlobObject, setup: Setup, version_36: bool = True) -> str:
    """POV-Ray scene reproducing the original StimBlob_call_*.pov files for this object."""
    lines = []
    if version_36:
        # pre-3.7 semantics: no gamma handling, i.e. identical to the 2008 renders
        lines.append("#version 3.6;")
    lines += ['#include "colors.inc"', "background{Black}", "camera {",
              "  angle %.10g" % setup.cam_angle,
              "  right <%.10g,0,0>" % setup.cam_right,
              "  location %s" % _vec(setup.cam_location),
              "  look_at %s" % _vec(setup.cam_look_at), "}",
              "light_source { %s color White }" % _vec(setup.light)
              + ("" if setup.shadows else " // (shadowless requested)"),
              "#declare StimBlob = blob {", "  threshold %.10g" % obj.threshold]
    for c in obj.components:
        if c.radius <= 0 or c.strength == 0:
            continue
        lines += ["  sphere { %s, %.10g, %.10g  // %s" % (_vec(c.center), c.radius, c.strength, c.name),
                  "    translate %s" % _vec(c.translate),
                  "    scale %s" % _vec(pov_scale(c.scale)),
                  "    rotate %s" % _vec(c.rotate), "  }"]
    lines += ["}", "object{ StimBlob",
              "  rotate %s" % _vec(obj.rotate),
              "  translate %s" % _vec(obj.translate),
              "  scale %s" % _vec(pov_scale(obj.scale)),
              "  pigment {White}",
              "  finish { phong 0.0 ambient %.10g diffuse %.10g }" % (obj.ambient, obj.diffuse),
              "}"]
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------------------
# Minimal POV-Ray parser (enough for the blob stimulus files)
# ----------------------------------------------------------------------------------------
_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", " ", text)


def _parse_vector(s: str, declared=None):
    """Parse '<a, b, c>' (commas optional, as POV-Ray allows) or a scalar."""
    s = s.strip()
    declared = declared or {}
    if s.startswith("<"):
        inner = s[1:s.index(">")]
        for k, v in declared.items():
            inner = re.sub(r"\b%s\b" % re.escape(k), str(v), inner)
        vals = [float(x) for x in re.findall(_NUM, inner)]
        if len(vals) != 3:
            raise ValueError(f"cannot parse vector {s!r}")
        return np.array(vals)
    m = re.match(_NUM, s)
    if m:
        return np.full(3, float(m.group(0)))
    for k, v in declared.items():
        if s.startswith(k):
            return np.full(3, float(v))
    raise ValueError(f"cannot parse value {s!r}")


def _block(text: str, start: int) -> Tuple[str, int]:
    """Return the contents of the {...} block whose '{' is at/after `start`."""
    i = text.index("{", start)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j + 1
    raise ValueError("unbalanced braces")


def _transforms(body: str, declared=None):
    ops = []
    for m in re.finditer(r"\b(translate|scale|rotate)\s*(<[^>]*>|%s)" % _NUM, body):
        ops.append((m.group(1), _parse_vector(m.group(2), declared)))
    return ops


def parse_pov(text: str, declared=None):
    """Parse a blob stimulus scene. Returns (BlobObject, Setup).

    Supports the constructs used by the Cox-lab / Zoccolan-lab stimulus files:
    ``camera{angle location look_at [right]}``, ``light_source{<pos> ...}``,
    ``blob{threshold  sphere{<c>, r, [strength] s  translate/scale/rotate ...} ...}``
    and ``object{ Name rotate/translate/scale ... finish{ambient diffuse} }``.
    Free identifiers (e.g. obj_pos_x set with Declare= on the command line) can be
    given in `declared`.
    """
    declared = dict(declared or {})
    text = _strip_comments(text)
    for m in re.finditer(r"#declare\s+(\w+)\s*=\s*(%s)\s*;" % _NUM, text):
        declared[m.group(1)] = float(m.group(2))
    setup = Setup()
    m = re.search(r"\bcamera\s*{", text)
    if m:
        body, _ = _block(text, m.start())
        if (a := re.search(r"\bangle\s+(%s)" % _NUM, body)):
            setup.cam_angle = float(a.group(1))
        if (a := re.search(r"\blocation\s*(<[^>]*>)", body)):
            setup.cam_location = _parse_vector(a.group(1), declared)
        if (a := re.search(r"\blook_at\s*(<[^>]*>)", body)):
            setup.cam_look_at = _parse_vector(a.group(1), declared)
        if (a := re.search(r"\bright\s*(<[^>]*>)", body)):
            setup.cam_right = float(np.linalg.norm(_parse_vector(a.group(1), declared)))
    m = re.search(r"\blight_source\s*{", text)
    if m:
        body, _ = _block(text, m.start())
        setup.light = _parse_vector(re.search(r"<[^>]*>", body).group(0), declared)
    m = re.search(r"\bblob\s*{", text)
    if not m:
        raise ValueError("no blob{} found in POV-Ray text")
    body, end_blob = _block(text, m.start())
    thr = re.search(r"\bthreshold\s+(%s)" % _NUM, body)
    comps = []
    pos = 0
    while True:
        s = re.search(r"\bsphere\s*{", body[pos:])
        if not s:
            break
        sb, e = _block(body, pos + s.start())
        pos = pos + s.start() + (e - (pos + s.start()))
        head = re.match(r"\s*(<[^>]*>)\s*,\s*(%s)\s*,\s*(?:strength\s+)?(%s)" % (_NUM, _NUM), sb)
        if not head:
            raise ValueError("cannot parse blob sphere component: %r" % sb[:80])
        center = _parse_vector(head.group(1), declared)
        ops = _transforms(sb[head.end():], declared)
        comp = Component(radius=float(head.group(2)), strength=float(head.group(3)), center=center)
        kinds = [k for k, _ in ops]
        order = ["translate", "scale", "rotate"]
        if len(set(kinds)) != len(kinds) or kinds != sorted(kinds, key=order.index):
            raise ValueError("blob component transforms must be (a subset of) translate, scale, "
                             "rotate in this order; got %s" % kinds)
        for k, v in ops:
            setattr(comp, k, v if k != "scale" else pov_scale(v))
        comps.append(comp)
    obj = BlobObject(components=comps, threshold=float(thr.group(1)) if thr else 1.0)
    # object{ <name> ... } that instantiates the blob (or transforms inside the blob itself)
    om = re.search(r"\bobject\s*{", text[end_blob:])
    obody = _block(text, end_blob + om.start())[0] if om else body[pos:]
    for k, v in _transforms(obody, declared):
        if k == "rotate":
            obj.rotate = v
        elif k == "translate":
            obj.translate = v
        elif k == "scale":
            obj.scale = pov_scale(v)
    if (a := re.search(r"\bambient\s+(%s)" % _NUM, obody)):
        obj.ambient = float(a.group(1))
    if (a := re.search(r"\bdiffuse\s+(%s)" % _NUM, obody)):
        obj.diffuse = float(a.group(1))
    return obj, setup
