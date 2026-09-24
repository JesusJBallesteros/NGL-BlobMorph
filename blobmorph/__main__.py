# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""Command line:  python -m blobmorph imageA.png imageB.png [options]

Examples
  python -m blobmorph A.png B.png --levels 9 --sizes 10 20 30 40 50 --out results
  python -m blobmorph --config my_config.json
  python -m blobmorph --model-a objA.pov --model-b objB.pov --levels 11 --out results
"""
from __future__ import annotations

import argparse
import json
import sys


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m blobmorph",
                                description="Morph matrix (morph levels x sizes) between two "
                                            "POV-Ray blob objects, following Rhee et al. (2025) "
                                            "and Zoccolan et al. (2009).")
    p.add_argument("image_a", nargs="?", help="image of object A (morph level 0 %%)")
    p.add_argument("image_b", nargs="?", help="image of object B (morph level 100 %%)")
    p.add_argument("--config", help="JSON file with options (command-line flags override it)")
    p.add_argument("--model-a", dest="model_a", help="blob model of A (.pov or .json)")
    p.add_argument("--model-b", dest="model_b", help="blob model of B (.pov or .json)")
    p.add_argument("--method", choices=["auto", "preset", "models", "fit"])
    p.add_argument("--setup", help="provided | zoccolan2009 | rhee2025 | JSON string")
    p.add_argument("--levels", dest="n_levels", type=int, help="number of morph levels incl. anchors")
    p.add_argument("--sizes", type=float, nargs="+", help="sizes in degrees of visual angle")
    p.add_argument("--sampling", choices=["arc", "chord", "original", "uniform"])
    p.add_argument("--n-dense", dest="n_dense", type=int)
    p.add_argument("--dense-scale", dest="dense_scale", type=float)
    p.add_argument("--correspondence", choices=["match", "crossfade", "index"])
    p.add_argument("--vanish", choices=["fade", "shrink"])
    p.add_argument("--center", choices=["anchors", "none"])
    p.add_argument("--size-reference", dest="size_reference",
                   choices=["crop_max", "crop_width", "crop_height", "object_max"])
    p.add_argument("--px-per-deg", dest="px_per_deg", type=float)
    p.add_argument("--screen-px", dest="screen_px", type=int, nargs=2)
    p.add_argument("--screen-cm", dest="screen_cm", type=float, help="screen width (cm)")
    p.add_argument("--distance-cm", dest="distance_cm", type=float, help="viewing distance (cm)")
    p.add_argument("--deg-mode", dest="deg_mode", choices=["mworks", "tangent", "linear"])
    p.add_argument("--display-gamma", dest="display_gamma", type=float)
    p.add_argument("--luminance-display", dest="luminance_display",
                   choices=["actual", "schematic"])
    p.add_argument("--no-screens", dest="save_screens", action="store_false", default=None)
    p.add_argument("--inputs-as-anchors", dest="use_inputs_as_anchors", action="store_true",
                   default=None)
    p.add_argument("--processes", type=int)
    p.add_argument("--out", dest="out_dir")
    p.add_argument("--title")
    p.add_argument("--quiet", dest="verbose", action="store_false", default=None)
    args = p.parse_args(argv)

    cfg = {}
    if args.config:
        with open(args.config, encoding="utf-8") as f:
            cfg.update(json.load(f))
    for k, v in vars(args).items():
        if k == "config" or v is None:
            continue
        cfg[k] = v
    if isinstance(cfg.get("setup"), str) and cfg["setup"].strip().startswith("{"):
        cfg["setup"] = json.loads(cfg["setup"])
    from .pipeline import run
    manifest = run(cfg)
    print("manifest:", manifest.get("figure"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
