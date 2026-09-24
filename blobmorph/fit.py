# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""Recover a POV-Ray blob model from a single image (analysis by synthesis).

Used when the input images are not the known objects: the image is explained by a blob made
of K ellipsoidal components (POV-Ray ``sphere { <0,0,0>, 0.8, 1  translate scale rotate }``,
threshold 0.2 - "a particular configuration and blend of three starting spheres", Rhee et
al. 2025) rendered with the same camera, light, finish and tone curve as the stimuli.

* initialisation : Gaussian-mixture decomposition of the silhouette into lobes, each lobe
                   -> an ellipsoid (orientation, extent, fixed depth);
* structure      : left-right symmetric objects (auto-detected) are parametrised with midline
                   components and mirrored pairs (like the two ears of object 2); several
                   structures (e.g. an extra, silhouette-invisible component such as the
                   "nose" of object 1) are tried and the best one kept;
* optimisation   : CMA-ES on the squared pixel error, coarse-to-fine, parallel evaluation.

A single view does not determine depth uniquely; the fitted model reproduces the image and
gives smooth 3-D morphs, but its parameters need not equal the original scene file.
"""
from __future__ import annotations

import math
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import render as R
from . import tone as tonemod
from .scene import BlobObject, Component, Setup, pov_rotation
from .stimuli import BBOX_LEVEL, resize

RADIUS = 0.8
SURF = math.sqrt(1.0 - math.sqrt(0.2))  # visible radius / influence radius (isolated, s=1)


# ------------------------------------------------------------------------------------------
# CMA-ES (Hansen 2016, "The CMA Evolution Strategy: A Tutorial")
# ------------------------------------------------------------------------------------------
class CMAES:
    def __init__(self, x0, sigma0, popsize=None, seed=0):
        n = len(x0)
        self.n = n
        self.xmean = np.asarray(x0, float).copy()
        self.sigma = float(sigma0)
        self.lam = int(popsize or 4 + int(3 * np.log(n)))
        self.mu = self.lam // 2
        w = np.log(self.mu + 0.5) - np.log(np.arange(1, self.mu + 1))
        self.w = w / w.sum()
        self.mueff = 1.0 / np.sum(self.w ** 2)
        self.cc = (4 + self.mueff / n) / (n + 4 + 2 * self.mueff / n)
        self.cs = (self.mueff + 2) / (n + self.mueff + 5)
        self.c1 = 2 / ((n + 1.3) ** 2 + self.mueff)
        self.cmu = min(1 - self.c1, 2 * (self.mueff - 2 + 1 / self.mueff) / ((n + 2) ** 2 + self.mueff))
        self.damps = 1 + 2 * max(0.0, np.sqrt((self.mueff - 1) / (n + 1)) - 1) + self.cs
        self.pc = np.zeros(n)
        self.ps = np.zeros(n)
        self.B = np.eye(n)
        self.D = np.ones(n)
        self.C = np.eye(n)
        self.invsqrtC = np.eye(n)
        self.chiN = np.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n ** 2))
        self.rng = np.random.default_rng(seed)
        self.gen = 0
        self.best = (np.inf, self.xmean.copy())

    def ask(self):
        z = self.rng.standard_normal((self.lam, self.n))
        return self.xmean + self.sigma * (z * self.D) @ self.B.T

    def tell(self, X, f):
        f = np.asarray(f, float)
        idx = np.argsort(f)
        if f[idx[0]] < self.best[0]:
            self.best = (float(f[idx[0]]), X[idx[0]].copy())
        X = X[idx]
        old = self.xmean
        self.xmean = self.w @ X[:self.mu]
        y = (self.xmean - old) / self.sigma
        self.ps = (1 - self.cs) * self.ps + np.sqrt(self.cs * (2 - self.cs) * self.mueff) * (self.invsqrtC @ y)
        self.gen += 1
        hsig = (np.linalg.norm(self.ps) / np.sqrt(1 - (1 - self.cs) ** (2 * self.gen)) / self.chiN
                < 1.4 + 2 / (self.n + 1))
        self.pc = (1 - self.cc) * self.pc + hsig * np.sqrt(self.cc * (2 - self.cc) * self.mueff) * y
        art = (X[:self.mu] - old) / self.sigma
        self.C = ((1 - self.c1 - self.cmu) * self.C
                  + self.c1 * (np.outer(self.pc, self.pc) + (1 - hsig) * self.cc * (2 - self.cc) * self.C)
                  + self.cmu * (art.T * self.w) @ art)
        self.sigma *= np.exp((self.cs / self.damps) * (np.linalg.norm(self.ps) / self.chiN - 1))
        self.C = np.triu(self.C) + np.triu(self.C, 1).T
        d2, self.B = np.linalg.eigh(self.C)
        self.D = np.sqrt(np.maximum(d2, 1e-20))
        self.invsqrtC = (self.B / self.D) @ self.B.T


# ------------------------------------------------------------------------------------------
# Parametrisation
# ------------------------------------------------------------------------------------------
class Structure:
    """Parameter vector <-> BlobObject.

    'mid'  component: [y, z, log ax, log ay, log az, rx]           (x = 0, ry = rz = 0)
    'pair' component: [x, y, z, log ax, log ay, log az, rx, ry, rz] (+ mirror image)
    'free' component: [x, y, z, log ax, log ay, log az, rx, ry, rz]
    Semi-axes are those of the influence ellipsoid (sphere radius 0.8 x POV-Ray scale).
    """

    SIZES = {"mid": 6, "pair": 9, "free": 9}
    SCALES = {"pos": 0.12, "log": 0.15, "ang": 12.0}

    def __init__(self, kinds, threshold=0.2):
        self.kinds = list(kinds)
        self.threshold = threshold
        self.n = sum(self.SIZES[k] for k in self.kinds)

    def unit_scales(self):
        s = []
        P, L, A = self.SCALES["pos"], self.SCALES["log"], self.SCALES["ang"]
        for k in self.kinds:
            s += [P, P, L, L, L, A] if k == "mid" else [P, P, P, L, L, L, A, A, A]
        return np.array(s)

    @staticmethod
    def _component(c, axes, rot, name):
        scale = np.asarray(axes, float) / RADIUS
        rmat = pov_rotation(rot)
        translate = (rmat.T @ np.asarray(c, float)) / scale
        return Component(radius=RADIUS, strength=1.0, translate=translate, scale=scale,
                         rotate=np.asarray(rot, float), name=name)

    def to_object(self, theta) -> BlobObject:
        comps = []
        i = 0
        for j, k in enumerate(self.kinds):
            if k == "mid":
                y, z, la, lb, lc, rx = theta[i:i + 6]
                comps.append(self._component([0.0, y, z], np.exp([la, lb, lc]), [rx, 0, 0],
                                             "mid%d" % j))
                i += 6
            else:
                x, y, z, la, lb, lc, rx, ry, rz = theta[i:i + 9]
                ax = np.exp([la, lb, lc])
                comps.append(self._component([x, y, z], ax, [rx, ry, rz], "%s%d" % (k, j)))
                if k == "pair":
                    comps.append(self._component([-x, y, z], ax, [rx, -ry, -rz], "%s%d_mirror" % (k, j)))
                i += 9
        return BlobObject(components=comps, threshold=self.threshold, name="fitted")


# ------------------------------------------------------------------------------------------
# Silhouette analysis and initialisation
# ------------------------------------------------------------------------------------------
def _gmm(points, k, iters=60, seed=0):
    """Plain EM for a 2-D Gaussian mixture. Returns (weights, means, covs, loglik)."""
    rng = np.random.default_rng(seed)
    n = len(points)
    # k-means++ style init
    means = [points[rng.integers(n)]]
    for _ in range(1, k):
        d2 = np.min([np.sum((points - m) ** 2, 1) for m in means], axis=0)
        means.append(points[rng.choice(n, p=d2 / d2.sum())])
    means = np.array(means, float)
    covs = np.array([np.cov(points.T) / k for _ in range(k)])
    wts = np.full(k, 1.0 / k)
    ll = -np.inf
    for _ in range(iters):
        logp = np.zeros((n, k))
        for j in range(k):
            c = covs[j] + 1e-6 * np.eye(2)
            inv = np.linalg.inv(c)
            dx = points - means[j]
            logp[:, j] = (np.log(wts[j]) - 0.5 * np.einsum("ni,ij,nj->n", dx, inv, dx)
                          - 0.5 * np.log(np.linalg.det(c)) - np.log(2 * np.pi))
        mx = logp.max(1, keepdims=True)
        p = np.exp(logp - mx)
        s = p.sum(1, keepdims=True)
        ll_new = float(np.sum(mx[:, 0] + np.log(s[:, 0])))
        r = p / s
        nk = r.sum(0) + 1e-12
        wts = nk / n
        means = (r.T @ points) / nk[:, None]
        for j in range(k):
            dx = points - means[j]
            covs[j] = (r[:, j, None] * dx).T @ dx / nk[j]
        if abs(ll_new - ll) < 1e-6 * abs(ll_new):
            break
        ll = ll_new
    return wts, means, covs, ll_new


def symmetry_score(mask):
    """IoU between the silhouette and its mirror image about the bbox centre column."""
    ys, xs = np.nonzero(mask)
    cx = (xs.min() + xs.max()) / 2.0
    xm = np.round(2 * cx - xs).astype(int)
    ok = (xm >= 0) & (xm < mask.shape[1])
    mirrored = np.zeros_like(mask)
    mirrored[ys[ok], xm[ok]] = True
    return (mask & mirrored).sum() / float((mask | mirrored).sum()), cx


def _pixel_to_world(u, v, setup: Setup, W, H, z):
    loc, d, r, up = R.camera_basis(setup)
    x0 = u / W - 0.5
    y0 = 0.5 - v / H
    ray = d + x0 * r + y0 * up
    t = (z - loc[2]) / ray[2]
    p = loc + t * ray
    return p, t * np.linalg.norm(r) / W  # world size of one pixel at that depth


def initial_structures(img, setup: Setup, symmetric="auto", max_components=4, depth=None,
                       verbose=False):
    """Candidate (Structure, theta0) pairs from a silhouette decomposition."""
    H, W = img.shape
    mask = img > BBOX_LEVEL
    sym_iou, cx_img = symmetry_score(mask)
    is_sym = (sym_iou > 0.95) if symmetric == "auto" else bool(symmetric)
    if verbose:
        print("  silhouette symmetry IoU %.3f -> %s" % (sym_iou, "symmetric" if is_sym else "free"))
    z0 = depth if depth is not None else 5.5
    ys, xs = np.nonzero(mask)
    pts = np.stack([xs, ys], 1).astype(float)
    if len(pts) > 20000:
        pts = pts[np.random.default_rng(0).choice(len(pts), 20000, replace=False)]
    # number of lobes: smallest mixture whose union of 2-sigma ellipses explains the silhouette
    # (a BIC choice over-segments the uniform ellipses of blob silhouettes)
    small = mask[::4, ::4]
    gy, gx = np.mgrid[0:small.shape[0], 0:small.shape[1]] * 4.0
    fits = []
    for k in range(1, max_components + 1):
        best_k = None
        for seed in range(k, k + 60, 10):  # several EM starts (EM has local optima)
            w, m, c, ll = _gmm(pts, k, seed=seed)
            union = np.zeros_like(small)
            for j in range(k):
                inv = np.linalg.inv(c[j] + 1e-6 * np.eye(2))
                dx, dy = gx - m[j][0], gy - m[j][1]
                union |= (inv[0, 0] * dx * dx + 2 * inv[0, 1] * dx * dy + inv[1, 1] * dy * dy) <= 4.0
            iou = (union & small).sum() / float((union | small).sum())
            if best_k is None or iou > best_k[0]:
                best_k = (iou, w, m, c, k)
            if k == 1:
                break
        fits.append(best_k)
    best = None
    for f in fits:
        if best is None or f[0] > best[0] + 0.02:  # a lobe must add > 2 % IoU
            best = f
    _, wts, means, covs, k = best
    lobes = []
    for j in range(k):
        evals, evecs = np.linalg.eigh(covs[j])
        a_px = 2.0 * np.sqrt(np.maximum(evals, 1e-6))  # semi-axes of a uniform ellipse
        ang = math.degrees(math.atan2(evecs[1, 1], evecs[0, 1]))  # major axis (image, v down)
        p, pix = _pixel_to_world(means[j][0], means[j][1], setup, W, H, z0)
        lobes.append({"center": p, "a_major": a_px[1] * pix / SURF, "a_minor": a_px[0] * pix / SURF,
                      "angle_world": -ang, "offset": (means[j][0] - cx_img) / W})
    if verbose:
        print("  %d lobes in the silhouette" % k)

    def comp_params(lobe, kind):
        c = lobe["center"]
        la, lb = math.log(max(lobe["a_major"], 1e-3)), math.log(max(lobe["a_minor"], 1e-3))
        lz = min(la, lb)
        # ellipse major axis along world x after rotation about z by the lobe angle
        if kind == "mid":
            # midline lobes: orient with rotation about x only -> use axes along x / y
            vert = abs(math.sin(math.radians(lobe["angle_world"]))) > 0.7
            ax_x, ax_y = (lb, la) if vert else (la, lb)
            return [c[1], c[2], ax_x, ax_y, lz, 0.0]
        return [c[0], c[1], c[2], la, lb, lz, 0.0, 0.0, lobe["angle_world"]]

    kinds, theta = [], []
    if is_sym:
        mids = [l for l in lobes if abs(l["offset"]) < 0.04]
        # off-midline lobes: mirror right ones to the left, merge duplicates -> pairs
        sides = []
        for l in lobes:
            if abs(l["offset"]) < 0.04:
                continue
            if l["offset"] > 0:
                c = l["center"].copy()
                c[0] = -c[0]
                l = dict(l, center=c, angle_world=-l["angle_world"], offset=-l["offset"])
            if not any(np.linalg.norm(l["center"] - s["center"]) < 0.5 * min(l["a_major"], s["a_major"])
                       for s in sides):
                sides.append(l)
        for l in mids:
            kinds.append("mid")
            theta += comp_params(l, "mid")
        for l in sorted(sides, key=lambda l: l["center"][1]):
            kinds.append("pair")
            theta += comp_params(l, "pair")
        if not kinds:
            kinds, theta = ["mid"], comp_params(lobes[0], "mid")
    else:
        for l in lobes:
            kinds.append("free")
            theta += comp_params(l, "free")
    return [(Structure(kinds), np.array(theta, float))], is_sym


def residual_components(img_target, rendered, depth, setup: Setup, W, H, symmetric, cx_img,
                        max_candidates=2):
    """Candidate extra components placed where the image is least explained.

    Coherent same-sign regions of the (smoothed; mirror-averaged for symmetric objects)
    residual inside the silhouette are ranked by their summed residual - e.g. the 'nose'
    of object 1, visible only through its shading.  Each region gives the position (on the
    rendered surface) and extent of a new component.  Returns [(kind, params), ...]."""
    from scipy import ndimage
    h, w = rendered.shape
    inside = ndimage.binary_erosion((img_target > BBOX_LEVEL) & np.isfinite(depth), iterations=2)
    if inside.sum() < 20:
        return []
    r = ndimage.gaussian_filter(np.asarray(img_target, float) - rendered, 1.5)
    r[~inside] = 0.0
    cxl = cx_img * w / float(W) - 0.5  # symmetry column in low-res pixel indices
    if symmetric:
        cols = np.arange(w)
        mc = np.clip(np.round(2 * cxl - cols).astype(int), 0, w - 1)
        r = 0.5 * (r + r[:, mc])
    peak = np.abs(r).max()
    if peak < 6.0:  # less than ~6 grey levels left to explain
        return []
    thr = max(4.0, 0.35 * peak)
    big = np.abs(r) > thr
    oys, oxs = np.nonzero(inside)
    obj_w = oxs.max() - oxs.min() + 1
    obj_h = oys.max() - oys.min() + 1
    tan_half = np.tan(np.deg2rad(setup.cam_angle) / 2.0)

    def make(kind, reg, u=None):
        ys, xs = np.nonzero(reg)
        wts = np.abs(r[ys, xs])
        if u is None:
            u = np.sum(wts * xs) / wts.sum() + 0.5
        v = np.sum(wts * ys) / wts.sum() + 0.5
        iy = int(min(h - 1, max(0, round(v - 0.5))))
        ix = int(min(w - 1, max(0, round(u - 0.5))))
        t = depth[iy, ix] if np.isfinite(depth[iy, ix]) else np.nanmedian(depth[inside])
        dvec = R.primary_directions(setup, np.array([u]), np.array([v]), w, h)[0]
        p = setup.cam_location + t * dvec
        pix = t * 2.0 * tan_half / w  # world size of one low-res pixel at that distance
        ext_px = np.array([np.clip(xs.max() - xs.min() + 1, 0.08 * obj_w, 0.6 * obj_w),
                           np.clip(ys.max() - ys.min() + 1, 0.08 * obj_h, 0.6 * obj_h)])
        ax = np.log(ext_px * pix / 2.0 / SURF)
        az = float(ax.min())
        if kind == "mid":
            return kind, [p[1], p[2], ax[0], ax[1], az, 0.0]
        return kind, [p[0], p[1], p[2], ax[0], ax[1], az, 0.0, 0.0, 0.0]

    out = []
    if symmetric:
        # midline candidate: strongest same-sign residual region crossing the symmetry axis
        # (e.g. the dark 'tongue' of object 1, flanked by bright rims of the base)
        cols = np.arange(w)[None, :]
        near_axis = np.abs(cols - cxl) <= 0.15 * obj_w
        best_mid = None
        for sign in (1, -1):
            lab, n = ndimage.label(ndimage.binary_closing(sign * r > thr, iterations=1) & inside)
            for k in np.unique(lab[near_axis & (lab > 0)]):
                reg = lab == k
                sc = float(np.abs(r[reg]).sum())
                if reg.sum() >= 3 and (best_mid is None or sc > best_mid[0]):
                    best_mid = (sc, reg)
        if best_mid is not None:
            out.append((best_mid[0], make("mid", best_mid[1], u=cxl + 0.5)))
        # lateral candidate: strongest region on the left of the axis (mirror-averaged map)
        side = big & (cols < cxl - 0.15 * obj_w)
        lab, n = ndimage.label(side)
        best = None
        for k in range(1, n + 1):
            reg = lab == k
            sc = float(np.abs(r[reg]).sum())
            if reg.sum() >= 3 and (best is None or sc > best[0]):
                best = (sc, reg)
        if best is not None:
            out.append((best[0], make("pair", best[1])))
    else:
        lab, n = ndimage.label(ndimage.binary_closing(big, iterations=1) & inside)
        regs = sorted(((float(np.abs(r[lab == k]).sum()), lab == k) for k in range(1, n + 1)
                       if (lab == k).sum() >= 3), key=lambda x: -x[0])
        out = [(sc, make("free", reg)) for sc, reg in regs[:max_candidates]]
    out.sort(key=lambda x: -x[0])
    return [c for _, c in out[:max_candidates]]


# ------------------------------------------------------------------------------------------
# Objective (evaluated in worker processes)
# ------------------------------------------------------------------------------------------
_G = {}


def _init_worker(target, setup, w, h, ss, tone_spec, threshold):
    _G.update(target=target, setup=setup, w=w, h=h, ss=ss, threshold=threshold,
              f=tonemod.tone_function(tone_spec), cache={})
    R.N_SAMPLES = 24 if w < 300 else 32


def _objective(job):
    kinds, theta = job
    g = _G
    st = g["cache"].get(tuple(kinds))
    if st is None:
        st = g["cache"][tuple(kinds)] = Structure(kinds, g["threshold"])
    try:
        lin = R.render(st.to_object(theta), g["setup"], g["w"], g["h"], supersample=g["ss"],
                       antialias=False)
    except Exception:
        return 1e3
    d = (g["f"](lin) - g["target"]) / 255.0
    return float(np.mean(d * d))


class Evaluator:
    """Pool of worker processes rendering candidate models at one resolution."""

    def __init__(self, img, setup, res, ss, tone_spec, threshold, processes):
        H, W = img.shape
        self.w, self.h = max(24, int(round(W * res))), max(18, int(round(H * res)))
        self.target = resize(img, self.w / float(W)).astype(float)
        self.pool = ProcessPoolExecutor(
            max_workers=processes, initializer=_init_worker,
            initargs=(self.target, setup, self.w, self.h, ss, tone_spec, threshold))

    def __call__(self, kinds, thetas):
        return list(self.pool.map(_objective, [(list(kinds), th) for th in thetas]))

    def close(self):
        self.pool.shutdown()


def _run_cmaes(ev, structure, theta0, sigma0, max_gens, popsize, seed, verbose, label,
               free=None):
    """CMA-ES on the parameters `free` (indices; default all), others fixed at theta0."""
    scales = structure.unit_scales()
    free = np.arange(structure.n) if free is None else np.asarray(free)
    es = CMAES(np.zeros(free.size), sigma0, popsize=popsize, seed=seed)
    t0 = time.time()

    def full(x):
        th = np.array(theta0, float)
        th[free] += x * scales[free]
        return th

    # the starting point is a candidate too (a stage must never make the fit worse)
    f0 = ev(structure.kinds, [full(np.zeros(free.size))])[0]
    es.best = (f0, np.zeros(free.size))
    last_best, stall = f0, 0
    for gen in range(max_gens):
        X = es.ask()
        f = ev(structure.kinds, [full(x) for x in X])
        es.tell(X, f)
        if es.best[0] < last_best * (1 - 1e-3):
            last_best, stall = es.best[0], 0
        else:
            stall += 1
        if verbose and (gen % 25 == 0 or gen == max_gens - 1):
            print("    %s gen %3d  best rms %.2f grey levels  sigma %.3f  (%.0f s)" % (
                label, gen, 255 * math.sqrt(es.best[0]), es.sigma, time.time() - t0), flush=True)
        if stall > 40 or es.sigma < 1e-3:
            break
    return full(es.best[1]), es.best[0]


def _parent_block(st: Structure, theta, point):
    """Parameter indices of the structure block contributing most density at `point`."""
    obj = st.to_object(theta)
    cb = R.CompiledBlob(obj, min_extent=0.0)
    dens = []
    for k in range(cb.K):
        x = cb.W[k] @ point + cb.w[k]
        q = float(x @ x) * cb.inv_r2[k]
        dens.append(cb.s[k] * max(1.0 - q, 0.0) ** 2)
    comp = int(np.argmax(dens))
    # map object component index -> structure block (pairs create two components)
    start, ci = 0, 0
    for kind in st.kinds:
        n_comp = 2 if kind == "pair" else 1
        if ci <= comp < ci + n_comp:
            return np.arange(start, start + Structure.SIZES[kind])
        ci += n_comp
        start += Structure.SIZES[kind]
    return np.arange(0)


def fit_image(img, setup: Setup, symmetric="auto", max_components=4, max_extra=2,
              stages=((0.15, 2, 160, 1.0), (0.3, 2, 70, 0.3), (0.5, 1, 40, 0.1)),
              popsize=16, processes=8, restarts=1, seed=0, verbose=True, tone=None, depth=None):
    """Fit a blob model to a grey image (0..255 floats). Returns a dict with 'object'.

    stages: (resolution factor, supersampling, max generations, initial sigma) per stage.
    The structure comes from the silhouette (lobes -> midline components / mirror pairs);
    up to `max_extra` components are then added where the shading is not explained
    (kept only if the error drops by > 15 %), and the model is refined at higher resolution.
    """
    img = np.asarray(img, dtype=float)
    H, W = img.shape
    setup = setup.copy()
    setup.width, setup.height = W, H
    if abs(W / float(H) - setup.cam_right / setup.cam_up) > 0.01:
        setup.cam_right = setup.cam_up * W / float(H)  # square pixels for other aspect ratios
    setup.shift = (0, 0)
    tone_spec = tone or setup.tone
    cands, is_sym = initial_structures(img, setup, symmetric, max_components, depth, verbose)
    _, cx_img = symmetry_score(img > BBOX_LEVEL)
    evs = {}

    def ev(i):
        if i not in evs:
            res, ss, _, _ = stages[i]
            evs[i] = Evaluator(img, setup, res, ss, tone_spec, 0.2, processes)
        return evs[i]

    def label(st, i):
        return "structure %s, stage %d (%dx%d)" % ("+".join(st.kinds), i, ev(i).w, ev(i).h)

    try:
        st, th0 = cands[0]
        gens0, sig0 = stages[0][2], stages[0][3]
        best = None
        for rep in range(restarts):
            theta, err = _run_cmaes(ev(0), st, th0.copy(), sig0, gens0, popsize, seed + 100 * rep,
                                    verbose, label(st, 0))
            if best is None or err < best[0]:
                best = (err, theta)
        err, theta = best
        if verbose:
            print("  silhouette structure %s: rms %.2f grey levels" % (
                "+".join(st.kinds), 255 * math.sqrt(err)))
        # greedily add components where the shading is not explained (hidden parts)
        w0, h0 = ev(0).w, ev(0).h
        for _ in range(max_extra):
            lin, dep = R.render(st.to_object(theta), setup, w0, h0, antialias=False,
                                return_depth=True)
            rendered0 = tonemod.tone_function(tone_spec)(lin)
            cands_extra = residual_components(ev(0).target, rendered0, dep, setup, W, H, is_sym,
                                              cx_img)
            trial = None
            for kind, params in cands_extra:
                st_new = Structure(st.kinds + [kind], st.threshold)
                nfree = Structure.SIZES[kind]
                # free: the new component and its 'parent' (the existing part with the largest
                # density where the new one is placed: it has absorbed the missing volume)
                pos = np.array([0.0, params[0], params[1]] if kind == "mid" else params[:3], float)
                parent = _parent_block(st, theta, pos)
                free = np.concatenate([parent, np.arange(len(theta), len(theta) + nfree)])
                # 1) multi-start over tilt, protrusion depth and elongation
                #    (a hidden part such as the nose of object 1 is inclined and in front)
                tilt_idx, z_idx, ay_idx = (5, 1, 3) if kind == "mid" else (6, 2, 4)
                depth_axis = math.exp(params[4] if kind == "mid" else params[5])
                starts = []
                for tilt in (-45.0, 0.0, 45.0):
                    for dz in (0.5, 1.0):
                        for elong in (1.0, 1.8):
                            p = np.array(params, float)
                            p[tilt_idx] = tilt
                            p[z_idx] -= dz * depth_axis  # towards the camera
                            p[ay_idx] += math.log(elong)
                            starts.append(np.concatenate([theta, p]))
                results_new = []
                for k, th_new in enumerate(starts):
                    results_new.append(_run_cmaes(ev(0), st_new, th_new, 1.0, 25, popsize,
                                                  seed + 7 * len(st.kinds) + k, False, "", free))
                results_new.sort(key=lambda x: x[1])
                # 2) continue the two best starts, then all parameters together
                best2 = None
                for th2, e2 in results_new[:2]:
                    th3, e3 = _run_cmaes(ev(0), st_new, th2, 0.5, gens0 // 3, popsize,
                                         seed + 11 * len(st.kinds), verbose,
                                         "new %s component + parent" % kind, free)
                    if best2 is None or e3 < best2[1]:
                        best2 = (th3, e3)
                theta2, err2 = _run_cmaes(ev(0), st_new, best2[0], 0.25, gens0 // 3, popsize,
                                          seed + 13 * len(st.kinds), verbose, label(st_new, 0))
                if verbose:
                    print("  + %s component: rms %.2f -> %.2f grey levels" % (
                        kind, 255 * math.sqrt(err), 255 * math.sqrt(err2)))
                if trial is None or err2 < trial[0]:
                    trial = (err2, st_new, theta2)
                if err2 < 0.85 * err:
                    break  # good enough: do not try the other candidates
            if trial is not None and trial[0] < 0.85 * err:
                err, st, theta = trial
            else:
                break
        for i in range(1, len(stages)):
            theta, err = _run_cmaes(ev(i), st, theta, stages[i][3], stages[i][2], popsize,
                                    seed + 1000 * i, verbose, label(st, i))
    finally:
        for e in evs.values():
            e.close()
    obj = st.to_object(theta)
    lin = R.render(obj, setup)
    rendered = tonemod.apply_tone(lin, tone_spec)
    m1, m2 = rendered > BBOX_LEVEL, img > BBOX_LEVEL
    iou = float((m1 & m2).sum() / max((m1 | m2).sum(), 1))
    diff = np.abs(rendered.astype(float) - img)
    mae_obj = float(diff[m1 | m2].mean())
    if verbose:
        print("  best: %s, full-resolution MAE on the object %.2f grey levels, silhouette IoU "
              "%.4f" % ("+".join(st.kinds), mae_obj, iou))
    return {"object": obj, "setup": setup, "structure": st.kinds, "theta": theta.tolist(),
            "rms_fit": 255 * math.sqrt(err), "mae_object": mae_obj,
            "mae_image": float(diff.mean()), "iou_full": iou, "symmetric": is_sym,
            "render": rendered}
