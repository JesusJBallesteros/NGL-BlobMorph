# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""Morph continuum between two blob objects and equal pixel-distance sampling.

Rhee et al. (2025), STAR Methods: the spheres of one object are shifted parametrically into
the spheres of the other; 2000 morphs are generated and 22 of them are sub-sampled at equal
Euclidean pixel distance between successive morphs.

Implementation (julianarhee/morph-pov): every parameter of every blob component (translate,
scale, rotate, radius, strength) and of the object transform is linearly interpolated
between two endpoint objects with the same component list (make_pov_morphs.py, linmap);
components that exist in only one object are faded (strength -> 0) or shrunk (radius -> 0).
The rendered continuum is then sampled at equal cumulative Euclidean distance
(utils/euclid.py, get_even_dists_euclidean, "neighbor" mode).
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import render as R
from . import tone as tonemod
from .scene import BlobObject, Component, Setup

_COMP_FIELDS = ("radius", "strength", "translate", "scale", "rotate", "center")
_OBJ_FIELDS = ("threshold", "rotate", "translate", "scale", "ambient", "diffuse")


def interpolate(a: BlobObject, b: BlobObject, t: float, mode: str = "pov") -> BlobObject:
    """Morph between two objects with matching component lists.

    mode 'pov'       : linear interpolation of all POV-Ray numbers (translate, scale, rotate,
                       radius, strength, object transform) - the original make_pov_morphs.py
    mode 'geometric' : world-space interpolation of each ellipsoid (centre linear, semi-axes
                       linear after aligning the axes, orientation by slerp), robust for
                       fitted models whose Euler angles / axis order are arbitrary
    """
    if mode == "geometric":
        return _interpolate_geometric(a, b, t)
    if len(a.components) != len(b.components):
        raise ValueError("endpoint objects must have the same number of components")
    comps = []
    for ca, cb in zip(a.components, b.components):
        kw = {f: (1 - t) * np.asarray(getattr(ca, f), float) + t * np.asarray(getattr(cb, f), float)
              for f in _COMP_FIELDS}
        comps.append(Component(name=ca.name or cb.name, **kw))
    kw = {f: (1 - t) * np.asarray(getattr(a, f), float) + t * np.asarray(getattr(b, f), float)
          for f in _OBJ_FIELDS}
    kw["threshold"] = float(kw["threshold"])
    kw["ambient"] = float(kw["ambient"])
    kw["diffuse"] = float(kw["diffuse"])
    return BlobObject(components=comps, name="morph_t%.6f" % t, **kw)


def pov_euler_from_matrix(r):
    """Angles (deg) such that scene.pov_rotation(angles) == r (r = Rz Ry Rx)."""
    sy = -np.clip(r[2, 0], -1.0, 1.0)
    ay = np.arcsin(sy)
    if abs(np.cos(ay)) > 1e-8:
        ax = np.arctan2(r[2, 1], r[2, 2])
        az = np.arctan2(r[1, 0], r[0, 0])
    else:  # gimbal lock
        ax = np.arctan2(-r[1, 2], r[1, 1])
        az = 0.0
    return np.rad2deg([ax, ay, az])


def _ellipsoid(obj: BlobObject, c: Component):
    """World-space centre, orientation (proper rotation) and semi-axes of a component."""
    centre, e = _comp_geometry(obj, c)       # e = M * radius
    u, s, _ = np.linalg.svd(e)
    if np.linalg.det(u) < 0:
        u[:, 2] *= -1
    return centre, u, s


def _rot_log(r):
    ang = np.arccos(np.clip((np.trace(r) - 1) / 2.0, -1.0, 1.0))
    if ang < 1e-9:
        return np.zeros(3)
    if np.pi - ang < 1e-6:  # 180 deg: axis from the symmetric part
        m = (r + np.eye(3)) / 2.0
        axis = m[:, np.argmax(np.diag(m))]
        return axis / np.linalg.norm(axis) * ang
    w = np.array([r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1]]) / (2 * np.sin(ang))
    return w * ang


def _rot_exp(v):
    ang = np.linalg.norm(v)
    if ang < 1e-12:
        return np.eye(3)
    k = v / ang
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K


def _align_axes(ua, sa, ub, sb):
    """Signed axis permutation of B closest (smallest rotation) to A."""
    import itertools
    best = None
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            u = ub[:, perm] * np.array(signs)
            if np.linalg.det(u) < 0:
                continue
            ang = np.linalg.norm(_rot_log(ua.T @ u))
            # prefer permutations that also keep the semi-axes similar
            cost = ang + 0.25 * np.abs(np.log(np.maximum(sb[list(perm)], 1e-9) /
                                             np.maximum(sa, 1e-9))).sum()
            if best is None or cost < best[0]:
                best = (cost, u, sb[list(perm)])
    return best[1], best[2]


def _interpolate_geometric(a: BlobObject, b: BlobObject, t: float) -> BlobObject:
    if len(a.components) != len(b.components):
        raise ValueError("endpoint objects must have the same number of components")
    comps = []
    for ca, cb in zip(a.components, b.components):
        strength = (1 - t) * ca.strength + t * cb.strength
        va, vb = ca.radius > 0, cb.radius > 0
        if not va and not vb:
            continue
        ga = _ellipsoid(a, ca) if va else None
        gb = _ellipsoid(b, cb) if vb else None
        if ga is None:   # grows from nothing at B's place
            ga = (gb[0], gb[1], np.zeros(3))
        if gb is None:
            gb = (ga[0], ga[1], np.zeros(3))
        (c0, u0, s0), (c1, u1, s1) = ga, gb
        u1, s1 = _align_axes(u0, s0, u1, s1)
        centre = (1 - t) * c0 + t * c1
        axes = (1 - t) * s0 + t * s1
        u = u0 @ _rot_exp(t * _rot_log(u0.T @ u1))
        if axes.min() <= 1e-9 or strength == 0:
            continue
        rot = pov_euler_from_matrix(u)
        r = RADIUS_GEOM
        scale = axes / r
        translate = (pov_rotation_cols(rot).T @ centre) / scale
        comps.append(Component(name=ca.name or cb.name, radius=r, strength=strength,
                               translate=translate, scale=scale, rotate=rot))
    thr = (1 - t) * a.threshold + t * b.threshold
    return BlobObject(components=comps, threshold=float(thr), name="morph_t%.6f" % t,
                      ambient=float((1 - t) * a.ambient + t * b.ambient),
                      diffuse=float((1 - t) * a.diffuse + t * b.diffuse))


RADIUS_GEOM = 0.8


def pov_rotation_cols(angles):
    from .scene import pov_rotation
    return pov_rotation(angles)


# ------------------------------------------------------------------------------------------
# Building endpoints for arbitrary objects (component correspondence)
# ------------------------------------------------------------------------------------------
def symmetry_groups(obj: BlobObject, tol=0.02):
    """Classify components as left-right symmetric ('mid') or mirror pairs ('pair').

    Returns a list of ('mid', [i]) / ('pair', [left, right]) or None if the object is not
    symmetric about the plane x = 0 (in world coordinates)."""
    geo = [_comp_geometry(obj, c) for c in obj.components]
    mir = np.diag([-1.0, 1.0, 1.0])
    scale = np.mean([np.linalg.norm(m, 2) for _, m in geo]) + 1e-12

    def same(g1, g2):
        (c1, m1), (c2, m2) = g1, g2
        return (np.linalg.norm(c1 - c2) < tol * scale and
                np.linalg.norm(m1 @ m1.T - m2 @ m2.T) < tol * scale ** 2)

    groups, used = [], set()
    for i, (c, m) in enumerate(geo):
        if i in used or obj.components[i].radius <= 0:
            continue
        mg = (mir @ c, mir @ m)
        if same(geo[i], mg):
            groups.append(("mid", [i]))
            used.add(i)
            continue
        partner = None
        for j in range(len(geo)):
            if j != i and j not in used and same(geo[j], mg) and \
                    abs(obj.components[j].strength - obj.components[i].strength) < 1e-9:
                partner = j
                break
        if partner is None:
            return None
        left, right = (i, partner) if c[0] < 0 else (partner, i)
        groups.append(("pair", [left, right]))
        used.update((i, partner))
    return groups
def _faded(c: Component) -> Component:
    d = c.to_dict()
    d["strength"] = 0.0
    return Component.from_dict(d)


def _shrunk(c: Component) -> Component:
    return Component(name=c.name, radius=0.0, strength=c.strength, translate=[0, 0, 0],
                     scale=[0, 0, 0], rotate=[0, 0, 0])


def _comp_geometry(obj: BlobObject, c: Component):
    """World-space centre and ellipsoid matrix (semi-axes) of a component."""
    from .scene import affine_from_ops
    mo, bo = affine_from_ops(obj.object_ops())
    mc, bc = affine_from_ops(c.ops())
    m = mo @ mc
    centre = m @ c.center + mo @ bc + bo
    return centre, m * c.radius


def _cost_matrix(a: BlobObject, b: BlobObject):
    ga = [_comp_geometry(a, c) for c in a.components]
    gb = [_comp_geometry(b, c) for c in b.components]
    scale = np.mean([np.linalg.norm(m, 2) for _, m in ga + gb]) + 1e-9
    cost = np.zeros((len(ga), len(gb)))
    for i, (ca, ma) in enumerate(ga):
        for j, (cb, mb) in enumerate(gb):
            cost[i, j] = np.linalg.norm(ca - cb) / scale + \
                np.linalg.norm(ma @ ma.T - mb @ mb.T) / (scale ** 2)
    return cost


def match_components(a: BlobObject, b: BlobObject, max_cost=None):
    """Hungarian matching of components (centre distance + shape difference).

    If both objects are left-right symmetric, midline components are matched with midline
    components and mirror pairs with mirror pairs, so that every morph stays symmetric."""
    from scipy.optimize import linear_sum_assignment
    cost = _cost_matrix(a, b)
    ga, gb = symmetry_groups(a), symmetry_groups(b)

    def hungarian(rows, cols, sub):
        if not rows or not cols:
            return []
        ri, ci = linear_sum_assignment(sub)
        return [(rows[i], cols[j]) for i, j in zip(ri, ci)
                if max_cost is None or sub[i, j] <= max_cost]

    if ga is not None and gb is not None:
        pairs = []
        ma = [g[1][0] for g in ga if g[0] == "mid"]
        mb = [g[1][0] for g in gb if g[0] == "mid"]
        pairs += hungarian(ma, mb, cost[np.ix_(ma, mb)] if ma and mb else None)
        pa = [g[1] for g in ga if g[0] == "pair"]
        pb = [g[1] for g in gb if g[0] == "pair"]
        if pa and pb:
            sub = np.array([[cost[x[0], y[0]] for y in pb] for x in pa])
            for (x, y) in hungarian(list(range(len(pa))), list(range(len(pb))), sub):
                pairs += [(pa[x][0], pb[y][0]), (pa[x][1], pb[y][1])]
        return pairs, cost
    return hungarian(list(range(len(a.components))), list(range(len(b.components))), cost), cost


def build_endpoints(a: BlobObject, b: BlobObject, strategy="match", vanish="fade", max_cost=None):
    """Extended endpoint objects (same component list) for an arbitrary pair.

    strategy : 'match'     - matched components are interpolated; others fade in/out
               'crossfade' - every component of A fades out while every one of B fades in
               'index'     - component i of A is interpolated into component i of B
    vanish   : 'fade'   - unmatched components change strength (like the head disc/ears)
               'shrink' - unmatched components shrink to radius 0 (like the nose)
    """
    if strategy == "index":
        if len(a.components) != len(b.components):
            raise ValueError("'index' strategy needs the same number of components")
        pairs = [(i, i) for i in range(len(a.components))]
    elif strategy == "crossfade":
        pairs = []
    elif strategy == "match":
        pairs, _ = match_components(a, b, max_cost)
    else:
        raise ValueError("unknown strategy %r" % strategy)
    gone = _faded if vanish == "fade" else _shrunk
    ca, cb = [], []
    used_a = {i for i, _ in pairs}
    used_b = {j for _, j in pairs}
    for i, j in pairs:
        x, y = a.components[i], b.components[j]
        ca.append(x)
        cb.append(y)
    for i, x in enumerate(a.components):
        if i not in used_a:
            ca.append(x)
            cb.append(gone(x))
    for j, y in enumerate(b.components):
        if j not in used_b:
            ca.append(gone(y))
            cb.append(y)
    ea = BlobObject(components=ca, threshold=a.threshold, rotate=a.rotate, translate=a.translate,
                    scale=a.scale, ambient=a.ambient, diffuse=a.diffuse, name=a.name + "_ext")
    eb = BlobObject(components=cb, threshold=b.threshold, rotate=b.rotate, translate=b.translate,
                    scale=b.scale, ambient=b.ambient, diffuse=b.diffuse, name=b.name + "_ext")
    return ea, eb


# ------------------------------------------------------------------------------------------
# Rendering sequences
# ------------------------------------------------------------------------------------------
def _render_one(args):
    a, b, t, setup, width, height, supersample, full_quality = args
    obj = interpolate(a, b, t)
    if not full_quality:
        R.N_SAMPLES = 40
    lin = R.render(obj, setup, width=width, height=height, supersample=supersample,
                   antialias=(supersample <= 1 and setup.antialias))
    return lin.astype(np.float32)


def render_sequence(a, b, ts, setup: Setup, width=None, height=None, supersample=1,
                    processes=None, full_quality=True, progress=None):
    """Linear renders of interpolate(a, b, t) for all t (parallel over processes)."""
    jobs = [(a, b, float(t), setup, width, height, supersample, full_quality) for t in ts]
    n = len(jobs)
    procs = processes if processes is not None else max(1, min(os.cpu_count() or 1, 16))
    out = [None] * n
    if procs <= 1 or n <= 2:
        for i, j in enumerate(jobs):
            out[i] = _render_one(j)
            if progress:
                progress(i + 1, n)
        return out
    with ProcessPoolExecutor(max_workers=procs) as ex:
        for i, img in enumerate(ex.map(_render_one, jobs, chunksize=max(1, n // (4 * procs)))):
            out[i] = img
            if progress:
                progress(i + 1, n)
    return out


# ------------------------------------------------------------------------------------------
# Equal Euclidean-distance sampling
# ------------------------------------------------------------------------------------------
def neighbor_distances(images):
    """Euclidean distance between consecutive images (flattened pixel vectors)."""
    flat = [np.asarray(im, dtype=np.float64).ravel() for im in images]
    d = np.array([np.linalg.norm(flat[i + 1] - flat[i]) for i in range(len(flat) - 1)])
    cum = np.concatenate([[0.0], np.cumsum(d)])
    return d, cum


def sample_equal_distance(ts, cum, n_levels, mode="interp"):
    """Pick n_levels (anchors included) equally spaced in cumulative pixel distance.

    mode 'interp'  : invert the piecewise-linear cumulative-distance curve -> exact t values
    mode 'nearest' : choose dense morphs as utils/euclid.py does (anchors forced, nearest
                     cumulative distance for the others; duplicates possible if too coarse)
    Returns (t_values, dense_indices or None, target_distances).
    """
    ts = np.asarray(ts, dtype=float)
    total = cum[-1]
    targets = np.linspace(0.0, total, n_levels)
    if mode == "interp":
        # make cum strictly increasing for the inverse interpolation
        c = cum + np.arange(len(cum)) * 1e-12 * max(total, 1.0)
        t = np.interp(targets, c, ts)
        t[0], t[-1] = ts[0], ts[-1]  # anchors exactly
        return t, None, targets
    if mode == "nearest":
        idx = [0]
        for tau in targets[1:]:
            idx.append(1 + int(np.argmin(np.abs(cum[1:] - tau))))
        idx = sorted(idx)
        return ts[idx], np.array(idx), targets
    raise ValueError("unknown sampling mode %r" % mode)


def distance_images(linear_images, tone_spec):
    """Images on which distances are measured: the 8-bit stimulus values (as float)."""
    return [tonemod.apply_tone(im, tone_spec).astype(np.float32) for im in linear_images]
