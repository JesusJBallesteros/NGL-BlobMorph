# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""End-to-end: two images (or two blob models) -> morph matrix (levels x sizes).

Steps (Rhee et al. 2025 STAR Methods + julianarhee/morph-pov + coxlab/povray_blobs):
 1. obtain the 3-D blob model of each input (known object, POV-Ray/JSON file, or fitted),
 2. build the morph continuum by linear interpolation of all blob parameters,
 3. render a dense continuum and choose `n_levels` morphs equally spaced in pixel-space
    Euclidean distance (anchors included),
 4. render the chosen morphs at full resolution, convert with the tone curve, centre the
    anchors' union bounding box, crop the union bounding box of all morphs,
 5. scale each morph to every requested size (degrees of visual angle), optionally paste
    it on a full screen and compute the luminance-matched full-field grey level,
 6. save stimuli, models (.json/.pov), manifest and the morph-matrix figure.
"""
from __future__ import annotations

import csv
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image

from . import figure as figmod
from . import morph as M
from . import presets
from . import render as R
from . import stimuli as S
from . import tone as tonemod
from .scene import BlobObject, Setup, load_object, load_setup, parse_pov, save_json, to_pov

DEFAULTS = {
    "image_a": None, "image_b": None,          # input images (object A = 0 %, B = 100 %)
    "model_a": None, "model_b": None,          # optional blob models (.pov / .json)
    "pov_declare": {},                         # values of free identifiers in .pov models
    "method": "auto",                          # auto | preset | models | fit
    "setup": "auto",                           # auto | provided | zoccolan2009 | rhee2025 | dict
    "n_levels": 9,                             # morph levels incl. both anchors
    "sizes": [10, 20, 30, 40, 50],             # degrees of visual angle
    "sampling": "arc",                         # arc | chord | original | uniform
    "n_dense": None,                           # dense continuum (default 201; 2002 for original)
    "dense_scale": 0.5,                        # resolution factor of the dense renders
    "dense_supersample": 2,
    "correspondence": "match",                 # match | crossfade | index (non-preset objects)
    "vanish": "fade",                          # fade | shrink
    "interpolation": "auto",                   # auto | pov | geometric
    "antialias": "auto",                       # final renders (auto: setup value)
    "center": "anchors",                       # anchors | none
    "center_horizontal": True,
    "crop_margin": 2,
    "size_reference": "crop_max",              # crop_max | crop_width | crop_height | object_max
    "px_per_deg": None, "screen_px": [1920, 1080], "screen_cm": None, "distance_cm": None,
    "deg_mode": "mworks", "stim_pos_deg": [0.0, 0.0],
    "save_screens": True, "display_gamma": 2.2, "luminance_column": True,
    "luminance_display": "actual",             # actual | schematic (paper figure: 255*size/max)
    "use_inputs_as_anchors": False,
    "save_frames": True, "save_pov": True,
    "processes": None, "fit": {}, "title": None, "out_dir": "morph_matrix_output",
    "verbose": True,
}


def _log(cfg, *a):
    if cfg.get("verbose", True):
        print("[blobmorph]", *a, flush=True)


def _default_processes():
    n = os.cpu_count() or 1
    return max(1, min(8, n // 2 if n > 2 else n))


def _setup_from(spec) -> Setup:
    if isinstance(spec, Setup):
        return spec.copy()
    if isinstance(spec, dict):
        base = presets.setup_for(spec.get("preset", "provided"))
        d = base.to_dict()
        d.update({k: v for k, v in spec.items() if k != "preset"})
        return Setup.from_dict(d)
    if spec in (None, "auto"):
        return presets.setup_for("provided")
    return presets.setup_for(spec)


# ------------------------------------------------------------------------------------------
# Dense continuum
# ------------------------------------------------------------------------------------------
def _dense_job(args):
    a, b, t, setup, w, h, ss, aa, nsamp, mode = args
    if nsamp:
        R.N_SAMPLES = nsamp
    lin = R.render(M.interpolate(a, b, t, mode), setup, width=w, height=h, supersample=ss,
                   antialias=aa)
    return tonemod.apply_tone(lin, setup.tone)


def iter_dense(a, b, ts, setup, w, h, ss, aa, processes, nsamp=None, mode="pov"):
    jobs = [(a, b, float(t), setup, w, h, ss, aa, nsamp, mode) for t in ts]
    if processes <= 1:
        for j in jobs:
            yield _dense_job(j)
        return
    with ProcessPoolExecutor(max_workers=processes) as ex:
        for img in ex.map(_dense_job, jobs, chunksize=max(1, len(jobs) // (8 * processes))):
            yield img


def choose_levels(a, b, setup, cfg, interp="pov"):
    """Return dict with t values of the morph levels and the dense distance profile."""
    n = int(cfg["n_levels"])
    mode = cfg["sampling"]
    procs = cfg["processes"] or _default_processes()
    if mode == "uniform":
        t = np.linspace(0.0, 1.0, n)
        return {"t": t, "levels": 100.0 * t, "ts_dense": None, "cum": None, "dense_idx": None}
    if mode == "original":
        # julianarhee/morph-pov: 2000 morphs + 2 anchors rendered at full size without AA,
        # neighbour Euclidean distances, nearest cumulative distance (utils/euclid.py)
        nd = int(cfg["n_dense"] or 2002)
        w, h, ss, aa = setup.width, setup.height, 1, False
    else:
        nd = int(cfg["n_dense"] or 201)
        w = max(16, int(round(setup.width * cfg["dense_scale"])))
        h = max(12, int(round(setup.height * cfg["dense_scale"])))
        ss, aa = int(cfg["dense_supersample"]), False
    ts = np.linspace(0.0, 1.0, nd)
    _log(cfg, "rendering dense continuum: %d morphs at %dx%d (x%d supersampling, %d processes)"
         % (nd, w, h, ss * ss, procs))
    t0 = time.time()
    prev, dists, keep = None, [], []
    for i, img in enumerate(iter_dense(a, b, ts, setup, w, h, ss, aa, procs, mode=interp)):
        x = img.astype(np.float32).ravel()
        if prev is not None:
            dists.append(float(np.linalg.norm(x - prev)))
        prev = x
        if mode == "chord":
            keep.append(x)
        if cfg.get("verbose", True) and (i + 1) % max(1, nd // 10) == 0:
            _log(cfg, "  %d/%d (%.0f s)" % (i + 1, nd, time.time() - t0))
    cum = np.concatenate([[0.0], np.cumsum(dists)])
    if mode == "arc":
        t, idx, _ = M.sample_equal_distance(ts, cum, n, "interp")
    elif mode == "original":
        t, idx, _ = M.sample_equal_distance(ts, cum, n, "nearest")
    elif mode == "chord":
        t = _equal_chords(ts, np.stack(keep), n)
        idx = None
    else:
        raise ValueError("unknown sampling %r" % mode)
    return {"t": np.asarray(t, float), "levels": np.linspace(0, 100, n), "ts_dense": ts,
            "cum": cum, "dense_idx": None if idx is None else [int(i) for i in idx]}


def _equal_chords(ts, X, n):
    """t values (anchors included) whose successive direct pixel distances are all equal."""
    def image_at(t):
        i = min(int(np.searchsorted(ts, t, side="right") - 1), len(ts) - 2)
        w = (t - ts[i]) / (ts[i + 1] - ts[i])
        return (1 - w) * X[i] + w * X[i + 1]

    def next_t(t0, delta):
        x0 = image_at(t0)
        d = np.linalg.norm(X - x0[None, :], axis=1)
        start = int(np.searchsorted(ts, t0, side="right"))
        for i in range(start, len(ts)):
            if d[i] >= delta:
                # linear refinement between i-1 (or t0) and i
                tp = max(ts[i - 1], t0) if i > 0 else t0
                dp = np.linalg.norm(image_at(tp) - x0)
                if d[i] - dp <= 1e-12:
                    return ts[i]
                return tp + (delta - dp) / (d[i] - dp) * (ts[i] - tp)
        return None

    def walk(delta):
        pts = [0.0]
        for _ in range(n - 1):
            t1 = next_t(pts[-1], delta)
            if t1 is None:
                return pts, False
            pts.append(t1)
        return pts, True

    lo = 0.0
    hi = float(np.linalg.norm(X[-1] - X[0]))
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        pts, ok = walk(mid)
        if ok and pts[-1] < 1.0:
            lo = mid           # all n-1 steps fit before the end: steps can be larger
        else:
            hi = mid
    pts, ok = walk(lo)
    pts = pts[:n] + [1.0] * max(0, n - len(pts))
    pts[-1] = 1.0
    return np.array(pts)


# ------------------------------------------------------------------------------------------
# Final renders
# ------------------------------------------------------------------------------------------
def _final_job(args):
    obj, setup, aa = args
    return R.render(obj, setup, antialias=aa).astype(np.float32)


def render_levels(objs, setup, aa, processes):
    jobs = [(o, setup, aa) for o in objs]
    if processes <= 1 or len(jobs) == 1:
        return [_final_job(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=processes) as ex:
        return list(ex.map(_final_job, jobs))


# ------------------------------------------------------------------------------------------
# Main entry
# ------------------------------------------------------------------------------------------
def _resolve_objects(cfg, imgs):
    """Return (A_ext, B_ext, setup, info) for the chosen method."""
    info = {}
    method = cfg["method"]
    ma, mb = cfg.get("model_a"), cfg.get("model_b")
    if method == "models" or (method == "auto" and ma and mb):
        if not (ma and mb):
            raise ValueError("method 'models' needs model_a and model_b")
        decl = cfg.get("pov_declare") or {}
        stored = None  # set-up saved with fitted models
        if str(ma).lower().endswith(".pov"):
            with open(ma, encoding="utf-8", errors="replace") as f:
                a, setup_model = parse_pov(f.read(), decl)
            if setup_model is not None:
                setup_model.tone = "linear"
        else:
            a, setup_model = load_object(ma, decl), load_setup(ma)
            stored = setup_model
        b = load_object(mb, decl)
        setup = setup_model if cfg["setup"] == "auto" and setup_model is not None \
            else _setup_from(cfg["setup"])
        if stored is not None and cfg["setup"] == "auto":
            _log(cfg, "rendering set-up stored with the fitted models: %dx%d, camera z = %g" % (
                setup.width, setup.height, setup.cam_location[2]))
        elif imgs is not None:
            # models + images: calibrate centring shift and tone curve on the images
            from .identify import calibrate_to_images
            setup, cal = calibrate_to_images(a, b, setup, imgs[0], imgs[1])
            info["calibration"] = cal
            _log(cfg, "models calibrated on the images: shift %s, silhouette IoU %.4f / %.4f, "
                 "tone MAE %.2f" % (setup.shift, cal["iou_a"], cal["iou_b"], cal["tone_mae"]))
        ea, eb = M.build_endpoints(a, b, cfg["correspondence"], cfg["vanish"])
        info.update(method="models", object_a=a.to_dict(), object_b=b.to_dict())
        return ea, eb, setup, info
    if imgs is None:
        raise ValueError("give image_a/image_b or model_a/model_b")
    if method in ("auto", "preset"):
        from .identify import identify_pair
        _log(cfg, "trying to recognise the inputs as the known objects (Zoccolan et al. 2009)")
        idp = identify_pair(imgs[0], imgs[1], cfg["image_a"], cfg["image_b"])
        if idp is not None:
            setup = idp["setup"]
            if cfg["setup"] not in ("auto", None):
                user = _setup_from(cfg["setup"])
                user.shift = setup.shift if isinstance(cfg["setup"], str) else user.shift
                setup = user
            a, b = presets.rhee_morph_endpoints(view=idp["view"])
            if idp["reversed"]:
                a, b = b, a
            info.update(method="preset", preset="zoccolan2009", identification={
                k: v for k, v in idp.items() if k != "setup"})
            _log(cfg, "recognised: A = object %d, B = object %d, camera z = %g, shift = %s, "
                 "tone = %s (MAE %.2f grey levels)" % (
                     idp["match_a"]["object"], idp["match_b"]["object"],
                     setup.cam_location[2], setup.shift,
                     setup.tone if isinstance(setup.tone, str) else "custom LUT", idp["tone_mae"]))
            return a, b, setup, info
        if method == "preset":
            raise RuntimeError("the input images were not recognised as the known objects")
        _log(cfg, "inputs not recognised -> fitting blob models to the images")
    # inverse rendering
    from .fit import fit_image
    setup = _setup_from(cfg["setup"])
    setup.width, setup.height = imgs[0].shape[1], imgs[0].shape[0]
    fits = []
    for k, img in enumerate(imgs):
        _log(cfg, "fitting blob model to image %s" % "AB"[k])
        res = fit_image(img, setup, processes=cfg["processes"] or _default_processes(),
                        verbose=cfg.get("verbose", True), **(cfg.get("fit") or {}))
        fits.append(res)
    a, b = fits[0]["object"], fits[1]["object"]
    setup = fits[0]["setup"]
    if cfg["setup"] in ("auto", None):
        setup.antialias = S.is_antialiased(imgs[0]) or S.is_antialiased(imgs[1])
    # keep the fitted models: re-use them with model_a/model_b (no refitting needed)
    mdir = os.path.join(os.path.abspath(cfg["out_dir"]), "models")
    for tag, fobj, fres in (("A", a, fits[0]), ("B", b, fits[1])):
        save_json(os.path.join(mdir, "fitted_%s.json" % tag),
                  dict(fobj.to_dict(), setup=setup.to_dict()))
        with open(os.path.join(mdir, "fitted_%s.pov" % tag), "w") as f:
            f.write(to_pov(fobj, setup))
        Image.fromarray(fres["render"]).save(os.path.join(mdir, "fitted_%s_render.png" % tag))
    _log(cfg, "fitted models saved in %s (fitted_A.json, fitted_B.json)" % mdir)
    ea, eb = M.build_endpoints(a, b, cfg["correspondence"], cfg["vanish"])
    info.update(method="fit", fit_a={k: v for k, v in fits[0].items() if k not in ("object", "setup", "render")},
                fit_b={k: v for k, v in fits[1].items() if k not in ("object", "setup", "render")},
                object_a=a.to_dict(), object_b=b.to_dict())
    return ea, eb, setup, info


def run(config=None, **kwargs):
    cfg = dict(DEFAULTS)
    cfg.update(config or {})
    cfg.update(kwargs)
    t_start = time.time()
    out = os.path.abspath(cfg["out_dir"])
    for sub in ("stimuli", "screens", "frames", "models", "figures"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    procs = cfg["processes"] or _default_processes()
    cfg["processes"] = procs

    imgs = None
    if cfg.get("image_a") and cfg.get("image_b"):
        imgs = [S.load_gray(cfg["image_a"]), S.load_gray(cfg["image_b"])]
        if imgs[0].shape != imgs[1].shape:
            raise ValueError("the two images must have the same size")

    a_ext, b_ext, setup, info = _resolve_objects(cfg, imgs)
    save_json(os.path.join(out, "models", "endpoint_A.json"), a_ext.to_dict())
    save_json(os.path.join(out, "models", "endpoint_B.json"), b_ext.to_dict())
    save_json(os.path.join(out, "models", "setup.json"), setup.to_dict())

    # 1) choose morph levels
    mode = cfg["interpolation"]
    if mode == "auto":
        fitted = info.get("method") == "fit" or (
            info.get("method") == "models" and
            info.get("object_a", {}).get("name") == "fitted" and
            info.get("object_b", {}).get("name") == "fitted")
        mode = "geometric" if fitted else "pov"
    info["interpolation"] = mode
    lv = choose_levels(a_ext, b_ext, setup, cfg, mode)
    t_levels = lv["t"]
    levels = np.asarray(lv["levels"], float)
    _log(cfg, "morph levels (%%): %s" % np.round(levels, 2).tolist())
    _log(cfg, "morph parameter t: %s" % np.round(t_levels, 4).tolist())

    # 2) final renders
    aa = setup.antialias if cfg["antialias"] == "auto" else bool(cfg["antialias"])
    if cfg["sampling"] == "original" and cfg["antialias"] == "auto":
        aa = False
    objs = [M.interpolate(a_ext, b_ext, float(t), mode) for t in t_levels]
    _log(cfg, "rendering %d morph levels at %dx%d" % (len(objs), setup.width, setup.height))
    lins = render_levels(objs, setup, aa, procs)
    frames = [S.place(tonemod.apply_tone(l, setup.tone), setup.shift, setup.frame_shape())
              for l in lins]
    if cfg["use_inputs_as_anchors"] and imgs is not None:
        frames[0] = np.clip(np.round(imgs[0]), 0, 255).astype(np.uint8)
        frames[-1] = np.clip(np.round(imgs[1]), 0, 255).astype(np.uint8)

    # 3) centring (anchors) and common crop
    shift = (0, 0)
    if cfg["center"] == "anchors":
        shift = S.centring_shift([frames[0], frames[-1]], horizontal=cfg["center_horizontal"])
        frames = [S.translate(f, shift) for f in frames]
    box = S.crop_box(frames, margin=int(cfg["crop_margin"]))
    crops = [f[box[0]:box[1], box[2]:box[3]] for f in frames]
    if cfg["save_frames"]:
        for j, f in enumerate(frames):
            Image.fromarray(f).save(os.path.join(out, "frames", "morph%02d_level%06.2f.png" % (j, levels[j])))

    # 4) sizes, screens, luminance
    disp = S.Display(cfg["px_per_deg"], cfg["screen_px"], cfg["screen_cm"], cfg["distance_cm"],
                     cfg["deg_mode"])
    sizes = [float(s) for s in cfg["sizes"]]
    stims, files, screens_files, lum = [], [], [], np.zeros((len(sizes), len(levels)))
    for i, size in enumerate(sizes):
        row, frow, srow = [], [], []
        for j, c in enumerate(crops):
            ref = S.reference_length(c.shape, cfg["size_reference"], S.bbox(c))
            scale = disp.size_px(size) / float(ref)
            st = S.resize(c, scale)
            row.append(st)
            name = "morph%02d_level%06.2f_size%05.1f.png" % (j, levels[j], size)
            p = os.path.join(out, "stimuli", name)
            Image.fromarray(st).save(p)
            frow.append(_rel(p, out))
            scr = S.compose_screen(st, disp, cfg["stim_pos_deg"])
            lum[i, j] = S.mean_luminance_level(scr, cfg["display_gamma"])
            if cfg["save_screens"]:
                ps = os.path.join(out, "screens", name)
                Image.fromarray(scr).save(ps)
                srow.append(_rel(ps, out))
        stims.append(row)
        files.append(frow)
        screens_files.append(srow)
    lum_per_size = lum.mean(axis=1)
    ff_files = []
    for i, size in enumerate(sizes):
        # full-field luminance control: one per size (averaged over morph levels, as in the paper)
        ff = np.full((disp.screen_px[1], disp.screen_px[0]), int(round(lum_per_size[i])), np.uint8)
        pf = os.path.join(out, "screens", "fullfield_luminance_size%05.1f.png" % size)
        Image.fromarray(ff).save(pf)
        ff_files.append(_rel(pf, out))

    # 5) models of every level
    for j, o in enumerate(objs):
        save_json(os.path.join(out, "models", "morph%02d.json" % j), o.to_dict())
        if cfg["save_pov"]:
            with open(os.path.join(out, "models", "morph%02d.pov" % j), "w") as f:
                f.write(to_pov(o, setup))

    # 6) figures
    title = cfg["title"]
    fig_png = os.path.join(out, "figures", "morph_matrix.png")
    fig_pdf = os.path.join(out, "figures", "morph_matrix.pdf")
    lum_fig = None
    if cfg["luminance_column"]:
        lum_fig = lum_per_size if cfg["luminance_display"] == "actual" else \
            255.0 * np.asarray(sizes) / max(sizes)
    panel = figmod.matrix_figure(stims, sizes, levels, fig_png, fig_pdf, luminance=lum_fig,
                                 title=title)
    Image.fromarray(panel).save(os.path.join(out, "figures", "morph_matrix_panel.png"))
    chords = [float(np.linalg.norm(crops[j + 1].astype(float) - crops[j].astype(float)))
              for j in range(len(crops) - 1)]
    figmod.distance_figure(lv["ts_dense"], lv["cum"], t_levels, levels, chords,
                           os.path.join(out, "figures", "distance_profile.png"),
                           title="sampling: %s" % cfg["sampling"])

    # 7) manifest
    manifest = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {k: v for k, v in cfg.items() if k not in ("verbose",)},
        "info": info,
        "setup": setup.to_dict(),
        "levels_percent": levels.tolist(),
        "t": [float(x) for x in t_levels],
        "dense_indices": lv["dense_idx"],
        "sizes_deg": sizes,
        "display": disp.describe(),
        "centering_shift": list(shift),
        "crop_box_rows_cols": list(box),
        "stimulus_files": files,
        "screen_files": screens_files,
        "luminance_ff_level": lum.tolist(),
        "luminance_ff_level_per_size": lum_per_size.tolist(),
        "fullfield_files": ff_files,
        "chord_distances_full_res": chords,
        "figure": _rel(fig_png, out),
        "elapsed_s": time.time() - t_start,
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=_json_default)
    with open(os.path.join(out, "manifest.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["level_index", "morph_level_percent", "t", "size_deg", "stimulus_file",
                    "screen_file", "width_px", "height_px", "luminance_ff_level"])
        for i, size in enumerate(sizes):
            for j in range(len(levels)):
                w.writerow([j, "%.4f" % levels[j], "%.6f" % t_levels[j], size, files[i][j],
                            screens_files[i][j] if screens_files[i] else "",
                            stims[i][j].shape[1], stims[i][j].shape[0], "%.3f" % lum[i, j]])
    _log(cfg, "done in %.0f s -> %s" % (time.time() - t_start, out))
    return manifest


def _rel(p, root):
    return os.path.relpath(p, root).replace(os.sep, "/")


def _json_default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, Setup):
        return o.to_dict()
    if isinstance(o, BlobObject):
        return o.to_dict()
    if isinstance(o, tuple):
        return list(o)
    return str(o)
