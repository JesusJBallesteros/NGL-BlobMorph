# NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).
"""Download an image set of the blob objects from https://github.com/coxlab/povray_blobs.

    python -m blobmorph.download                         # images/Blobs_TrainingRatsD1D2
    python -m blobmorph.download Blobs_TrainingRatsD1D2_FinerSampling --dest FOLDER

Default destination: <BlobMorph>/Images/<set name>.  The images are not distributed with
NGL BlobMorph; they belong to their authors (Cox lab).  Publications using them cite
Zoccolan et al. (2009).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

API = "https://api.github.com/repos/coxlab/povray_blobs/contents/images/{}"
DEFAULT_SET = "Blobs_TrainingRatsD1D2"
IMAGE_EXT = (".png", ".jpg", ".tif", ".bmp")


def download(set_name=DEFAULT_SET, dest=None):
    """Download all images of images/<set_name>; returns the list of saved files."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest = dest or os.path.join(root, "Images", set_name)
    os.makedirs(dest, exist_ok=True)
    with urllib.request.urlopen(API.format(set_name), timeout=60) as r:
        items = json.load(r)
    files = []
    for it in items:
        if it.get("type") != "file" or os.path.splitext(it["name"])[1].lower() not in IMAGE_EXT:
            continue
        target = os.path.join(dest, it["name"])
        urllib.request.urlretrieve(it["download_url"], target)
        files.append(target)
    print("%d images saved in %s" % (len(files), dest))
    return files


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m blobmorph.download")
    p.add_argument("set_name", nargs="?", default=DEFAULT_SET,
                   help="folder of images/ in coxlab/povray_blobs")
    p.add_argument("--dest", help="destination folder")
    a = p.parse_args(argv)
    download(a.set_name, a.dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
