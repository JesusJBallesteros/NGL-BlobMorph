# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""NumPy ray tracer reproducing POV-Ray's rendering of the blob stimuli.

Model (identical to POV-Ray 3.6/3.7 for these scenes):

* density of a blob component: s * (1 - d^2/r^2)^2 for d < r (0 elsewhere), with d the
  distance to the sphere centre measured in the component's own (un-transformed) frame;
  the surface is where the summed density equals the blob threshold;
* perspective camera defined by location / look_at / angle / right (default 1.33) / up;
* one white point light with hard shadows, finish { ambient A diffuse D phong 0 };
* optional POV-Ray style antialiasing (method 1: pixels whose colour differs from a
  neighbour by more than the threshold are supersampled with depth x depth rays).

The output is the *linear* intensity (what POV-Ray computes before writing the file);
`tone.py` converts it to 8-bit pixel values.
"""
from __future__ import annotations

import numpy as np

from .scene import BlobObject, Setup

CHUNK = 8192         # rays per chunk (memory / cache control)
N_SAMPLES = 48       # samples along each primary ray segment before bisection
N_SHADOW = 32        # samples along shadow rays
N_REFINE = 4         # 16-point bracket refinements of the first crossing (16^4 ~ 6.5e4)


class CompiledBlob:
    """Blob object reduced to arrays for fast evaluation of the density field."""

    def __init__(self, obj: BlobObject, min_extent=1e-6):
        aff = obj.component_affines()
        # skip components without influence: zero strength/radius, or so small (e.g. a
        # component shrinking to radius 0 in a morph) that they cannot change any pixel
        keep = []
        for i, c in enumerate(obj.components):
            if c.radius <= 0 or c.strength == 0:
                continue
            smin = 1.0 / np.linalg.svd(aff[i][0], compute_uv=False).max()
            if c.radius * smin < min_extent:
                continue
            keep.append(i)
        self.K = len(keep)
        if self.K == 0:
            self.W = np.zeros((0, 3, 3))
            self.w = np.zeros((0, 3))
        else:
            self.W = np.stack([aff[i][0] for i in keep])
            self.w = np.stack([aff[i][1] - obj.components[i].center for i in keep])
        self.inv_r2 = np.array([1.0 / obj.components[i].radius ** 2 for i in keep])
        self.s = np.array([obj.components[i].strength for i in keep])
        self.T = float(obj.threshold)
        self.ambient = float(obj.ambient)
        self.diffuse = float(obj.diffuse)

    # -- field -------------------------------------------------------------------------
    def quadratics(self, O, D):
        """Coefficients of q_k(t) = a t^2 + b t + c along rays O + t D. Arrays (K, N).

        O may be a single point (3,) shared by all rays (primary rays)."""
        WT = np.transpose(self.W, (0, 2, 1))
        g = np.matmul(D[None, :, :], WT)                       # (K, N, 3)
        ir = self.inv_r2[:, None]
        a = np.einsum("kni,kni->kn", g, g) * ir
        if O.ndim == 1:
            e = np.einsum("kij,j->ki", self.W, O) + self.w       # (K, 3)
            b = 2.0 * np.einsum("kni,ki->kn", g, e) * ir
            c = np.broadcast_to((np.einsum("ki,ki->k", e, e) * self.inv_r2)[:, None], a.shape)
        else:
            e = np.matmul(O[None, :, :], WT) + self.w[:, None, :]
            b = 2.0 * np.einsum("kni,kni->kn", e, g) * ir
            c = np.einsum("kni,kni->kn", e, e) * ir
        return a, b, c

    def field_t(self, a, b, c, t):
        """Density at parameters t (N, S) given quadratics (K, N) (dtype follows t)."""
        f = np.zeros(t.shape, dtype=t.dtype)
        q = np.empty_like(t)
        for k in range(self.K):
            np.multiply(a[k][:, None], t, out=q)
            q += b[k][:, None]
            q *= t
            q += c[k][:, None]
            np.subtract(1.0, q, out=q)
            np.maximum(q, 0.0, out=q)
            q *= q
            if self.s[k] != 1.0:
                q *= self.s[k]
            f += q
        return f

    def field_points(self, P):
        f = np.zeros(len(P))
        for k in range(self.K):
            x = P @ self.W[k].T + self.w[k]
            q = np.einsum("ni,ni->n", x, x) * self.inv_r2[k]
            u = np.maximum(1.0 - q, 0.0)
            f += self.s[k] * u * u
        return f

    def gradient(self, P):
        g = np.zeros_like(P)
        for k in range(self.K):
            x = P @ self.W[k].T + self.w[k]
            q = np.einsum("ni,ni->n", x, x) * self.inv_r2[k]
            coef = np.where(q < 1.0, self.s[k] * 2.0 * (1.0 - q) * (-2.0 * self.inv_r2[k]), 0.0)
            g += coef[:, None] * (x @ self.W[k])
        return g

    def ray_range(self, a, b, c, tmin, tmax):
        """Union of the influence intervals of the positive components along each ray."""
        n = a.shape[1]
        lo = np.full(n, np.inf)
        hi = np.full(n, -np.inf)
        for k in range(self.K):
            if self.s[k] <= 0:
                continue
            disc = b[k] ** 2 - 4.0 * a[k] * (c[k] - 1.0)
            ok = (disc > 0) & (a[k] > 0)
            sq = np.sqrt(np.where(ok, disc, 0.0))
            den = np.where(ok, 2.0 * a[k], 1.0)
            t0 = (-b[k] - sq) / den
            t1 = (-b[k] + sq) / den
            lo = np.where(ok, np.minimum(lo, t0), lo)
            hi = np.where(ok, np.maximum(hi, t1), hi)
        lo = np.maximum(lo, tmin)
        hi = np.minimum(hi, tmax)
        # upper bound of the density along the ray (each component at its closest approach);
        # rays that can never reach the threshold are discarded
        fmax = np.zeros(n)
        for k in range(self.K):
            if self.s[k] <= 0:
                continue
            qmin = c[k] - b[k] ** 2 / (4.0 * np.maximum(a[k], 1e-300))
            fmax += self.s[k] * np.maximum(1.0 - qmin, 0.0) ** 2
        hi = np.where(fmax >= self.T, hi, -np.inf)
        return lo, hi


def _shifted(a, b, c, lo):
    """Coefficients of q(lo + u) = a u^2 + b' u + c' (keeps float32 sampling accurate)."""
    return a, 2.0 * a * lo + b, (a * lo + b) * lo + c


def _sample(cb, a, b, c, span, nsamp):
    u = np.linspace(0.0, 1.0, nsamp, dtype=np.float32)
    uu = span.astype(np.float32)[:, None] * u[None, :]
    f = cb.field_t(a.astype(np.float32), b.astype(np.float32), c.astype(np.float32), uu)
    return uu, f


def _first_hit(cb: CompiledBlob, O, D, tmin, tmax, nsamp=None):
    """Parameter of the first surface crossing (outer side) or NaN."""
    nsamp = nsamp or N_SAMPLES
    n = len(D)
    out = np.full(n, np.nan)
    a, b, c = cb.quadratics(O, D)
    lo, hi = cb.ray_range(a, b, c, tmin, tmax)
    cand = np.nonzero(hi > lo)[0]
    if cand.size == 0:
        return out
    a, b, c = _shifted(a[:, cand], b[:, cand], c[:, cand], lo[cand])
    lo, span = lo[cand], (hi - lo)[cand]
    uu, f = _sample(cb, a, b, c, span, nsamp)
    above = f >= cb.T
    has = above.any(axis=1)
    idx = np.argmax(above, axis=1)
    u_in = np.where(has, uu[np.arange(len(idx)), idx], np.nan).astype(np.float64)
    u_out = np.where(has, uu[np.arange(len(idx)), np.maximum(idx - 1, 0)], np.nan).astype(np.float64)
    # grazing rays: a narrow crossing may fall between samples -> resample 4x finer
    near = np.nonzero(~has & (f.max(axis=1) >= 0.7 * cb.T))[0]
    if near.size:
        uu2, f2 = _sample(cb, a[:, near], b[:, near], c[:, near], span[near], 4 * nsamp)
        ab2 = f2 >= cb.T
        has2 = ab2.any(axis=1)
        i2 = np.argmax(ab2, axis=1)
        r = near[has2]
        k = np.nonzero(has2)[0]
        u_in[r] = uu2[k, i2[k]]
        u_out[r] = uu2[k, np.maximum(i2[k] - 1, 0)]
        has[r] = True
    sel = np.nonzero(has)[0]
    if sel.size == 0:
        return out
    aa, bb, cc = a[:, sel], b[:, sel], c[:, sel]
    uo, ui = u_out[sel], u_in[sel]
    # bracket refinement: 16 points per pass, keep the first outside/inside pair
    frac = np.linspace(0.0, 1.0, 17)[1:-1]
    rows = np.arange(sel.size)
    for _ in range(N_REFINE):
        um = uo[:, None] + (ui - uo)[:, None] * frac[None, :]
        ins = cb.field_t(aa, bb, cc, um) >= cb.T
        first = np.where(ins.any(axis=1), np.argmax(ins, axis=1), frac.size)
        new_ui = np.where(first < frac.size, um[rows, np.minimum(first, frac.size - 1)], ui)
        new_uo = np.where(first > 0, um[rows, np.maximum(first - 1, 0)], uo)
        ui, uo = new_ui, new_uo
    out[cand[sel]] = lo[sel] + uo
    return out


def _any_hit(cb: CompiledBlob, O, D, tmin, tmax, nsamp=None):
    nsamp = nsamp or N_SHADOW
    a, b, c = cb.quadratics(O, D)
    lo, hi = cb.ray_range(a, b, c, tmin, tmax)
    res = np.zeros(len(D), dtype=bool)
    cand = np.nonzero(hi > lo)[0]
    if cand.size == 0:
        return res
    a, b, c = _shifted(a[:, cand], b[:, cand], c[:, cand], lo[cand])
    span = (hi - lo)[cand]
    _, f = _sample(cb, a, b, c, span, nsamp)
    hit = (f >= cb.T).any(axis=1)
    near = np.nonzero(~hit & (f.max(axis=1) >= 0.7 * cb.T))[0]
    if near.size:
        _, f2 = _sample(cb, a[:, near], b[:, near], c[:, near], span[near], 4 * nsamp)
        hit[near] = (f2 >= cb.T).any(axis=1)
    res[cand] = hit
    return res


def camera_basis(setup: Setup):
    loc = setup.cam_location
    fwd = setup.cam_look_at - loc
    fwd = fwd / np.linalg.norm(fwd)
    sky = np.array([0.0, 1.0, 0.0])
    right = np.cross(sky, fwd)        # POV-Ray is left-handed: sky x direction = +x
    right = right / np.linalg.norm(right)
    up = np.cross(fwd, right)
    up = up / np.linalg.norm(up)
    dir_len = 0.5 * setup.cam_right / np.tan(np.deg2rad(setup.cam_angle) / 2.0)
    return loc, fwd * dir_len, right * setup.cam_right, up * setup.cam_up


def primary_directions(setup: Setup, px, py, width, height):
    """Ray directions through continuous pixel coordinates (px, py) (pixel i spans [i, i+1])."""
    loc, d, r, u = camera_basis(setup)
    x0 = px / width - 0.5
    y0 = 0.5 - py / height
    dirs = d[None, :] + x0[:, None] * r[None, :] + y0[:, None] * u[None, :]
    return dirs / np.linalg.norm(dirs, axis=1, keepdims=True)


def shade_rays(cb: CompiledBlob, setup: Setup, px, py, width, height, shadows=True,
               return_depth=False):
    """Linear intensity for rays through pixel coordinates (flat arrays)."""
    n = px.size
    val = np.zeros(n)
    depth = np.full(n, np.nan)
    if cb.K == 0:
        return (val, depth) if return_depth else val
    loc = setup.cam_location
    for s in range(0, n, CHUNK):
        sl = slice(s, min(n, s + CHUNK))
        D = primary_directions(setup, px[sl], py[sl], width, height)
        t = _first_hit(cb, loc, D, 1e-6, 1e9)
        hit = np.nonzero(np.isfinite(t))[0]
        if hit.size == 0:
            continue
        P = loc[None, :] + t[hit, None] * D[hit]
        g = cb.gradient(P)
        nrm = -g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-300)
        # POV-Ray flips normals facing away from the viewer
        flip = np.einsum("ni,ni->n", nrm, D[hit]) > 0
        nrm[flip] *= -1
        L = setup.light[None, :] - P
        dist = np.linalg.norm(L, axis=1)
        L = L / dist[:, None]
        ndl = np.einsum("ni,ni->n", nrm, L)
        lit = ndl > 0
        if shadows and lit.any():
            li = np.nonzero(lit)[0]
            occl = _any_hit(cb, P[li], L[li], 1e-5, dist[li])
            lit[li[occl]] = False
        v = cb.ambient + cb.diffuse * np.where(lit, ndl, 0.0)
        idx = np.arange(sl.start, sl.stop)[hit]
        val[idx] = v
        depth[idx] = t[hit]
    return (val, depth) if return_depth else val


def render(obj, setup: Setup, width=None, height=None, antialias=None, aa_threshold=None,
           aa_depth=None, supersample=1, shadows=None, return_depth=False):
    """Render `obj` (BlobObject or CompiledBlob) and return linear intensities (H, W).

    width/height default to setup.width/height (lower values keep the field of view, i.e.
    give a down-scaled rendering).  `supersample=k` shoots k x k rays in every pixel
    (box filter; used for fast low-resolution renders); otherwise POV-Ray-like adaptive
    antialiasing is applied when `antialias` is true.
    """
    cb = obj if isinstance(obj, CompiledBlob) else CompiledBlob(obj)
    W = int(width or setup.width)
    H = int(height or setup.height)
    shadows = setup.shadows if shadows is None else shadows
    antialias = setup.antialias if antialias is None else antialias
    aa_threshold = setup.aa_threshold if aa_threshold is None else aa_threshold
    aa_depth = setup.aa_depth if aa_depth is None else aa_depth
    k = int(supersample)
    if k > 1:
        off = (np.arange(k) + 0.5) / k
        jj, ii = np.meshgrid(np.arange(H), np.arange(W), indexing="ij")
        acc = np.zeros(H * W)
        for oy in off:
            for ox in off:
                acc += shade_rays(cb, setup, ii.ravel() + ox, jj.ravel() + oy, W, H, shadows)
        img = (acc / (k * k)).reshape(H, W)
        return img
    jj, ii = np.meshgrid(np.arange(H), np.arange(W), indexing="ij")
    img, depth = shade_rays(cb, setup, ii.ravel() + 0.5, jj.ravel() + 0.5, W, H, shadows,
                            return_depth=True)
    img = img.reshape(H, W)
    depth = depth.reshape(H, W)
    if antialias and aa_depth > 1:
        thr = aa_threshold / 3.0  # POV-Ray sums the differences of the R, G and B channels
        mark = np.zeros((H, W), dtype=bool)
        dx = np.abs(np.diff(img, axis=1)) > thr
        dy = np.abs(np.diff(img, axis=0)) > thr
        mark[:, 1:] |= dx
        mark[:, :-1] |= dx
        mark[1:, :] |= dy
        mark[:-1, :] |= dy
        ys, xs = np.nonzero(mark)
        if ys.size:
            n = aa_depth
            off = (np.arange(n) + 0.5) / n
            acc = np.zeros(ys.size)
            for oy in off:
                for ox in off:
                    acc += shade_rays(cb, setup, xs + ox, ys + oy, W, H, shadows)
            img[ys, xs] = acc / (n * n)
    return (img, depth) if return_depth else img
