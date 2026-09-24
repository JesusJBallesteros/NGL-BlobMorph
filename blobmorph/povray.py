# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""Optional: render the exported .pov scenes with the real POV-Ray.

    python -m blobmorph.povray OUTPUT_DIR [--width 1100 --height 825 --aa 0.3]

renders OUTPUT_DIR/models/morphNN.pov to morphNN_povray.png (linear POV-Ray output, i.e.
before the tone curve / centring applied by blobmorph).  On Windows the GUI build
(pvengine64.exe) is started with /EXIT /NR /RENDER; elsewhere the `povray` binary is used.
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
import time

WINDOWS_CANDIDATES = [
    r"C:\Program Files\POV-Ray\v3.7\bin\pvengine64.exe",
    r"C:\Program Files\POV-Ray\v3.8\bin\pvengine64.exe",
    r"C:\Program Files (x86)\POV-Ray\v3.7\bin\pvengine.exe",
]


def find_povray():
    exe = shutil.which("povray")
    if exe:
        return exe
    for c in WINDOWS_CANDIDATES:
        if os.path.isfile(c):
            return c
    return None


def render_pov(pov_path, out_png, width=1100, height=825, aa=0.3, exe=None, timeout=600):
    """Render one scene; returns True if the image was written."""
    exe = exe or find_povray()
    if exe is None:
        raise FileNotFoundError("POV-Ray not found (install it or put 'povray' on the PATH)")
    pov_path, out_png = os.path.abspath(pov_path), os.path.abspath(out_png)
    opts = ["+W%d" % width, "+H%d" % height, "-D", "+FN", "+O" + out_png]
    opts += ["+A%g" % aa] if aa is not None else ["-A"]
    if os.path.basename(exe).lower().startswith("pvengine"):
        args = [exe, "/EXIT", "/NR", "/RENDER", pov_path] + opts
    else:
        args = [exe, "+I" + pov_path] + opts
    if os.path.exists(out_png):
        os.remove(out_png)
    subprocess.run(args, timeout=timeout, cwd=os.path.dirname(pov_path),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while not os.path.exists(out_png) and time.time() - t0 < 10:
        time.sleep(0.2)
    return os.path.exists(out_png)


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m blobmorph.povray")
    p.add_argument("out_dir")
    p.add_argument("--width", type=int, default=1100)
    p.add_argument("--height", type=int, default=825)
    p.add_argument("--aa", type=float, default=0.3, help="antialias threshold (negative = off)")
    a = p.parse_args(argv)
    exe = find_povray()
    if exe is None:
        print("POV-Ray not found")
        return 1
    files = sorted(glob.glob(os.path.join(a.out_dir, "models", "morph*.pov")))
    for f in files:
        out = f[:-4] + "_povray.png"
        ok = render_pov(f, out, a.width, a.height, None if a.aa < 0 else a.aa, exe)
        print(("ok   " if ok else "FAIL ") + out, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
