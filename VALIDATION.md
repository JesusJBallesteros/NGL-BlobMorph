# Validation

Measured on 2026-09-23 and 2026-09-24. `python tests/validate.py` repeats the first table of
section 1, section 2 and section 3 (option `--figure FILE`: 1637 x 572 px crop of Fig. S4A).
Section 4: `examples/fitted_from_images`.

## 1. Built-in renderer and POV-Ray 3.7

Scenes `StimBlob_call_1.pov` and `StimBlob_call_2.pov` (camera z = -10, no antialiasing, POV-Ray
3.7 default sRGB output), 1100 x 825 px, rendered by POV-Ray 3.7.0 (`pvengine64.exe`) and by
`blobmorph.render`. Reference renders and scenes: `tests/povray_reference/`.

| Object | POV-Ray object pixels | Differing silhouette pixels | Mean absolute difference over the object |
|---|---|---|---|
| 1 | 249 636 | 2 | 0.03 grey levels |
| 2 | 191 360 | 2 | 0.03 grey levels |

Intermediate morph `models/morph04.pov` of a morph matrix (50 %, five components with
fractional strengths, camera z = -11, antialiasing threshold 0.3), rendered with
`python -m blobmorph.povray` and with the built-in renderer: mean absolute difference over the
object 0.13 grey levels, silhouette IoU 0.9993.

## 2. Re-rendered objects and image bank

Images `Blob_N1_CamRot_yRR.png` and `Blob_N2_CamRot_yRR.png` of the image bank (1078 x 617 px)
against the scene files rendered by `blobmorph.render` with the set-up found by the automatic
identification: camera z = -10, frame 1100 x 825 px, window offset (-131, -11) px, no
antialiasing, tone curve `zoccolan` (linear value 102 to 80, 150 to 128, 210 to 198, 255 to 254).

| RR (deg) | Object 1: MAE interior / edge / whole image | Object 1: IoU | Object 2: MAE interior / edge / whole image | Object 2: IoU |
|---|---|---|---|---|
| -90 | 0.56 / 0.48 / 0.18 | 1.0000 | 0.60 / 0.54 / 0.16 | 1.0000 |
| -75 | 0.58 / 0.58 / 0.19 | 1.0000 | 0.60 / 0.59 / 0.16 | 1.0000 |
| -60 | 0.59 / 0.49 / 0.20 | 1.0000 | 0.60 / 0.50 / 0.17 | 1.0000 |
| -45 | 0.60 / 0.50 / 0.22 | 1.0000 | 0.60 / 0.47 / 0.18 | 1.0000 |
| -30 | 0.61 / 0.47 / 0.22 | 1.0000 | 0.60 / 0.52 / 0.17 | 1.0000 |
| -15 | 0.62 / 0.55 / 0.23 | 1.0000 | 0.60 / 0.54 / 0.17 | 1.0000 |
| 0 | 0.63 / 0.48 / 0.24 | 1.0000 | 0.60 / 0.51 / 0.17 | 1.0000 |
| 15 | 0.62 / 0.56 / 0.23 | 1.0000 | 0.60 / 0.53 / 0.17 | 1.0000 |
| 30 | 0.61 / 0.46 / 0.22 | 1.0000 | 0.60 / 0.52 / 0.17 | 1.0000 |
| 45 | 0.60 / 0.49 / 0.22 | 1.0000 | 0.60 / 0.48 / 0.18 | 1.0000 |
| 60 | 0.59 / 0.48 / 0.20 | 1.0000 | 0.60 / 0.50 / 0.17 | 1.0000 |
| 75 | 0.58 / 0.58 / 0.19 | 1.0000 | 0.60 / 0.59 / 0.17 | 1.0000 |
| 90 | 0.56 / 0.48 / 0.18 | 1.0000 | 0.60 / 0.53 / 0.16 | 1.0000 |

MAE: mean absolute difference in grey levels over the union of both silhouettes eroded by
3 px (interior), over the rest of the union (edge) and over the whole image. IoU: silhouettes,
pixels > 40.

Anchors of Fig. S4A (`Blob_N1_5_...png` and `Blob_N2_5_...png`, 1100 x 825 px, not
distributed): camera z = -11, vertical centring of `ResizeBlobRatStims_General.m` (shift -22 px),
antialiasing, tone curve `zoccolan`.

| | MAE interior / edge / whole image | IoU |
|---|---|---|
| Object 1 | 0.63 / 2.83 / 0.16 | 0.9995 |
| Object 2 | 0.59 / 2.95 / 0.13 | 0.9993 |

## 3. Morph levels and Fig. S4A

Object bounding boxes of the 9 columns of Fig. S4A (rows 50, 40, 30 and 20 deg) against the
levels of each sampling rule (set-up of the anchors of Fig. S4A, best common scale per row):

| Levels | t (object A = 0, object B = 1) | Mean absolute error |
|---|---|---|
| `'uniform'` | 0, 0.125, 0.25, ..., 1 | 0.41 px |
| `M0, M14, ..., M106` (analysis code of Rhee et al.) | k / 106 | 0.42 px |
| equal distance, silhouettes only | 0, 0.113, 0.229, 0.349, 0.467, 0.584, 0.711, 0.854, 1 | 0.53 px |
| equal distance, sRGB images | 0, 0.108, 0.220, 0.338, 0.453, 0.568, 0.695, 0.843, 1 | 0.59 px |
| `'original'` (2002 frames, `euclid.py` rule) | 0, 0.090, 0.190, 0.302, 0.424, 0.553, 0.692, 0.845, 1 | 0.80 px |
| `'arc'` | 0, 0.082, 0.177, 0.287, 0.407, 0.530, 0.667, 0.827, 1 | 0.91 px |

Per-row errors of `'uniform'`: 0.44, 0.49, 0.35, 0.38 px.

## 4. Models fitted to the images

`Method = 'fit'` on `Blob_N1_CamRot_y0.png` and `Blob_N2_CamRot_y0.png` (set-up `'auto'`: camera
z = -11, square pixels, tone curve `zoccolan`; 8 processes; 37 min in total on a shared machine).
Result: `examples/fitted_from_images/`.

| Image | Fitted parts | Object-region MAE | Silhouette IoU |
|---|---|---|---|
| Object 1 | 2 midline parts, 2 mirrored pairs (6 parts; scene file: 3) | 11.9 | 0.992 |
| Object 2 | 2 midline parts, 1 mirrored pair (4 parts; scene file: 3) | 7.8 | 0.992 |
| Scene files, for comparison | | 0.63 / 0.59 | 1.0000 |

Object-region MAE: mean absolute grey-level difference over the union of both silhouettes
(pixels > 40). Part matching: midline parts to midline parts, first pair to first pair; the
second pair of object 1 fades out. All intermediate shapes are left-right symmetric.
