# NGL BlobMorph

MATLAB and Python tools that create a morph matrix (morph levels x stimulus sizes) between two
"blob" objects, as in Rhee et al. (2025), Fig. 1A and Fig. S4A. The objects are those of
Zoccolan et al. (2009).

Author: Jesus J. Ballesteros. Licence: MIT (`LICENSE`). Citation: `CITATION.cff`.

## Repository contents

```
BlobMorph\
    matlab\blobMorph_master.m           master script: all parameters as code, runs the morph
    matlab\blobMorph_live.m             live script: same parameters with controls, shows the results
    matlab\blobMorphMatrix.m            function called by both scripts
    matlab\blobMorphDownloadImages.m    downloads the image bank
    matlab\blobMorphPython.m            finds the Python interpreter
    matlab\blobMorphLoad.m              loads a results folder into MATLAB
    matlab\blobMorphReport.m            lists the files of a results folder
    blobmorph\                          Python back end
    examples\                           reference outputs
    tests\                              validation script, POV-Ray reference scenes and renders
    LICENSE, CITATION.cff, README.md, VALIDATION.md
```

Folders created locally and not part of the repository: `Images\` (image bank), `References\`
(reference papers), `results\` (default output folder of the scripts).

## Reference papers

| Reference | Relevant parts |
|---|---|
| Rhee JY, Echavarría C, Soucy E, Greenwood J, Masís JA, Cox DD (2025). Neural correlates of visual object recognition in rats. *Cell Reports* 44:115461. doi:10.1016/j.celrep.2025.115461 | Fig. 1A, Fig. S4A (morph matrix); STAR Methods: "Visual stimuli", "Identity-changing transformations", "Objects" |
| Zoccolan D, Oertelt N, DiCarlo JJ, Cox DD (2009). A rodent model for the study of invariant visual object recognition. *PNAS* 106:8748-8753. doi:10.1073/pnas.0811583106 | Fig. 1A (objects), Fig. 2 (sizes, rotations); Materials and Methods: "Visual Stimuli" |

The articles are available from the publishers (DOI links) and are not included in the
repository.

## Image bank

Folder `images/Blobs_TrainingRatsD1D2` of https://github.com/coxlab/povray_blobs (Cox lab):
objects 1 and 2 of Zoccolan et al. (2009) rendered with POV-Ray, 26 grey images of 1078 x 617 px.

| File | Content |
|---|---|
| `Blob_N1_CamRot_yRR.png` | object 1 (object A), rotation RR about the vertical axis |
| `Blob_N2_CamRot_yRR.png` | object 2 (object B), rotation RR about the vertical axis |

RR: -90 to 90 deg in steps of 15 deg; 0 is the default view (Zoccolan et al. 2009, Fig. 1A).

The images are not distributed with NGL BlobMorph. Download into `Images\Blobs_TrainingRatsD1D2`:
- MATLAB: `blobMorphDownloadImages` (other folders of `images/`: `blobMorphDownloadImages('<folder>')`).
- Python, from the `BlobMorph` folder: `python -m blobmorph.download`.
- git: `git clone https://github.com/coxlab/povray_blobs.git`, then copy
  `povray_blobs\images\Blobs_TrainingRatsD1D2\*.png` to `Images\Blobs_TrainingRatsD1D2\`.

Input images from other sources: grey renders (or white objects) on a black background, both
images of the same size. The two reference objects are recognised in full 4:3 POV-Ray frames of
any resolution and in windows of the 1100 x 825 frame (such as the image bank).

## Requirements

- MATLAB R2021a or later. No toolbox required. Controls of the live script: MATLAB R2025a or later.
- Python 3.9 or later with numpy, scipy, pillow and matplotlib.
- Internet access for the download of the image bank.
- Optional: POV-Ray 3.7 (renders the exported `.pov` scenes).
- About 5 MB of disk space per matrix of 9 levels x 5 sizes.

## Installation

1. Install Python from https://www.python.org/downloads/ (option "Add python.exe to PATH"), or
   use an Anaconda or Miniconda environment.
2. Install the packages in a Command Prompt or Terminal:
   ```
   python -m pip install numpy scipy pillow matplotlib
   ```
3. Check the installation:
   ```
   python -c "import numpy, scipy, PIL, matplotlib; print('ok')"
   ```
4. Clone or download the repository.
5. Download the image bank. In MATLAB, from the `BlobMorph\matlab` folder:
   ```
   blobMorphDownloadImages
   ```
6. Several Python installations: set `PythonExe` in section 10 of the scripts, or select the
   interpreter in MATLAB with `pyenv('Version', 'C:\path\to\python.exe')`.

## Creating a morph matrix

Master script:
1. Open `BlobMorph\matlab\blobMorph_master.m`.
2. Section 1: `ImageA` (level 0 %) and `ImageB` (level 100 %). Defaults: `Blob_N1_CamRot_y0.png`
   and `Blob_N2_CamRot_y0.png` of the image bank. Section 0: `OutputDir`, default
   `BlobMorph\results\morph_N1_N2`.
3. Sections 2 to 4: number of levels, sizes, spacing of the levels, display. Sections 5 to 10
   are needed only for other objects, special output options or performance settings.
4. Run the script (F5).
5. The results are in `OutputDir`. The folder content is printed at the end of the run.

Live script:
1. Open `BlobMorph\matlab\blobMorph_live.m` in the Live Editor (plain-text live script format).
2. Section 0: tick *Download image set* once if the image bank is missing.
3. Sections 1 to 10: set the parameters with the drop-down menus, check boxes, spinners, sliders,
   edit fields and file browsers.
4. Run the live script (Live Editor tab > Run). Section 11 checks the settings, section 12
   creates the morph matrix, sections 13 to 17 show the results and the location of the files.

MATLAB releases before R2025a open `blobMorph_live.m` as a plain script with the default values.
A binary live script: open `blobMorph_live.m` in the Live Editor, then Save As > Live Code File
(`*.mlx`).

The default settings reproduce Fig. S4A: 9 levels, sizes 10, 20, 30, 40 and 50 deg, level
spacing `'uniform'`, luminance column `'schematic'`.

Running time on 8 cores:

| Case | Time |
|---|---|
| objects 1 and 2, `Sampling = 'uniform'` | 15 to 30 s |
| objects 1 and 2, `'arc'` or `'chord'` | about 2 min |
| objects 1 and 2, `'original'` | about 25 min |
| other objects (models fitted to the images) | about 25 min |

## Parameters

Sections of `blobMorph_master.m` and `blobMorph_live.m`. Each parameter is described in the
scripts with examples from the project data.

| Section | Parameter | Default | Values |
|---|---|---|---|
| 0 | `OutputDir` | `results\morph_N1_N2` | folder |
| 1 | `ImageA`, `ImageB` | `Blob_N1_CamRot_y0.png`, `Blob_N2_CamRot_y0.png` | image files |
| 2 | `NumLevels` | 9 | 2 or more, both objects included |
| 2 | `Sizes` | `[10 20 30 40 50]` | degrees of visual angle |
| 2 | `Sampling` | `'uniform'` | `'uniform'` equal parameter steps; `'arc'` equal Euclidean pixel distance along the morph; `'chord'` equal distance between chosen levels; `'original'` procedure of julianarhee/morph-pov |
| 3 | `PixelsPerDegree` | 16.05 | px per deg; `[]` to use the screen geometry |
| 3 | `ScreenPixels`, `ScreenWidthCm`, `ViewingDistanceCm` | `[1920 1080]`, `[]`, `[]` | screen geometry |
| 3 | `DegreeMode` | `'mworks'` | `'mworks'`, `'tangent'`, `'linear'` |
| 3 | `StimulusPositionDeg` | `[0 0]` | stimulus centre on the screen images (deg) |
| 3 | `SizeReference` | `'crop_max'` | `'crop_max'`, `'crop_width'`, `'crop_height'`, `'object_max'` |
| 4 | `DisplayGamma` | 2.2 | gamma for the luminance-matched full-field levels |
| 4 | `SaveScreens` | true | full-screen images |
| 4 | `LuminanceDisplay` | `'schematic'` | `'actual'`, `'schematic'` |
| 4 | `FigureTitle` | `''` | text |
| 5 | `Method` | `'auto'` | `'auto'`, `'preset'`, `'fit'`, `'models'` |
| 5 | `ModelA`, `ModelB` | `''` | `.pov` or `.json` model files |
| 5 | `PovDeclare` | `struct()` | values of free identifiers in `.pov` files |
| 5 | `Setup` | `'auto'` | `'auto'`, `'provided'`, `'zoccolan2009'`, `'rhee2025'`, struct |
| 6 | `Correspondence` | `'match'` | `'match'`, `'crossfade'`, `'index'` |
| 6 | `Vanish` | `'fade'` | `'fade'`, `'shrink'` |
| 6 | `Interpolation` | `'auto'` | `'auto'`, `'pov'`, `'geometric'` |
| 7 | `FitSymmetric`, `FitMaxComponents`, `FitMaxExtra`, `FitRestarts`, `FitPopulation`, `FitSeed`, `FitStages` | see scripts | image fitting |
| 8 | `UseInputsAsAnchors`, `Center`, `CenterHorizontal`, `CropMargin`, `Antialias`, `SaveFrames`, `SavePov`, `LuminanceColumn` | see scripts | post-processing |
| 9 | `NumDense`, `DenseScale`, `DenseSupersample`, `Processes` | see scripts | performance |
| 10 | `PythonExe`, `Verbose`, `ShowFigure` | `''`, true, true | environment |

Function help: `help blobMorphMatrix`.

## Outputs

Contents of `OutputDir`:

| Path | Content |
|---|---|
| `figures\morph_matrix.png`, `.pdf` | morph matrix: sizes (rows, largest on top) x morph levels (columns), luminance column |
| `figures\morph_matrix_panel.png` | morph matrix without labels |
| `figures\distance_profile.png` | Euclidean pixel distance along the morph and between successive levels |
| `stimuli\morphLL_levelPPP.PP_sizeSSS.S.png` | stimulus of level LL (PPP.PP %) at size SSS.S deg, cropped |
| `screens\morphLL_levelPPP.PP_sizeSSS.S.png` | same stimulus on a full screen (`ScreenPixels`) |
| `screens\fullfield_luminance_sizeSSS.S.png` | full-field luminance control for each size |
| `frames\morphLL_levelPPP.PP.png` | frame of each level, same size as the input images |
| `models\morphLL.json`, `.pov` | 3-D model and POV-Ray scene of each level |
| `models\fitted_A.json`, `fitted_B.json` | fitted models with their rendering set-up (when models are fitted); reusable as `ModelA`, `ModelB` without refitting |
| `manifest.csv` | one row per stimulus: level index, morph level (%), morph parameter t, size (deg), files, size in px, full-field grey level |
| `manifest.json` | all settings and results |

MATLAB structure `R` (workspace after the run, or `R = blobMorphLoad(OutputDir)`):
`R.levels`, `R.t`, `R.sizes`, `R.stimuli{size, level}` (uint8 images), `R.files`, `R.screens`,
`R.luminance`, `R.lumPerSize`, `R.matrix`, `R.figureFile`, `R.manifest`.

## Method

1. Object models. Objects 1 and 2 are POV-Ray blobs (threshold 0.2) made of three ellipsoids
   each (scene files of coxlab/povray_blobs). Images of these objects are recognised; camera
   position, position of the image window in the rendered frame, grey tone curve and
   antialiasing are taken from the images (image bank: camera z = -10, window 1078 x 617 px,
   no antialiasing). Other images: blob models are fitted to the images (Method `'fit'`).
2. Morph continuum. Linear interpolation of all model parameters between the two objects
   (make_pov_morphs.py of julianarhee/morph-pov): base of object 1 to base of object 2, head disc
   strength 1 to 0, ear strength 0 to 1, nose radius 0.8 to 0, object position `<0,-0.18,5>` to
   `<0,0,6>`.
3. Morph levels. `'uniform'`: equal steps of the interpolation parameter (Fig. S4A). `'arc'`,
   `'chord'`, `'original'`: equal Euclidean distance between the images of successive levels
   (Rhee et al. 2025, STAR Methods: 2000 morphs, 22 levels).
4. Rendering. Built-in ray tracer equivalent to POV-Ray 3.7 for these scenes (VALIDATION.md).
5. Stimuli. Tone curve, centring of the joint bounding box of both objects, common crop of all
   levels, scaling so that the longest side of the crop spans each size, full-screen images,
   luminance-matched full-field grey level per size.

## Python command line

From the `BlobMorph` folder:
```
python -m blobmorph IMAGE_A IMAGE_B --levels 9 --sizes 10 20 30 40 50 --sampling uniform --out OUTPUT_DIR
python -m blobmorph --help
python -m blobmorph.download
python -m blobmorph.povray OUTPUT_DIR
```
`blobmorph.download` downloads the image bank; `blobmorph.povray` renders
`OUTPUT_DIR\models\morphLL.pov` with POV-Ray.

## Reference outputs

Figures, manifests and fitted models of two runs. Stimuli, screens, frames and per-level models
are not included.

| Folder | Content |
|---|---|
| `examples\reproduction_FigS4A` | `Blob_N1_CamRot_y0.png` and `Blob_N2_CamRot_y0.png` with the default settings |
| `examples\fitted_from_images` | the same images with `Method = 'fit'`; fitted models in `models\` |

Complete output folders, from the `BlobMorph` folder (image bank downloaded):
```
python -m blobmorph Images\Blobs_TrainingRatsD1D2\Blob_N1_CamRot_y0.png Images\Blobs_TrainingRatsD1D2\Blob_N2_CamRot_y0.png --levels 9 --sizes 10 20 30 40 50 --sampling uniform --luminance-display schematic --out results\reproduction_FigS4A
python -m blobmorph Images\Blobs_TrainingRatsD1D2\Blob_N1_CamRot_y0.png Images\Blobs_TrainingRatsD1D2\Blob_N2_CamRot_y0.png --method models --model-a examples\fitted_from_images\models\fitted_A.json --model-b examples\fitted_from_images\models\fitted_B.json --levels 9 --sizes 10 20 30 40 50 --sampling uniform --luminance-display schematic --out results\fitted_from_images
```
Running time: about 15 s each. MATLAB: master script with the default settings (first
command), or with `Method = 'models'` and the fitted models as `ModelA` and `ModelB` (section 5,
second command). Replacing `--method models --model-a ... --model-b ...` by `--method fit`
repeats the fit (about 25 min).

## Validation

`VALIDATION.md` lists the comparisons with POV-Ray, with the image bank and with Fig. S4A.
`python tests\validate.py` repeats them (Fig. S4A: option `--figure`).

## Troubleshooting

| Message | Action |
|---|---|
| ImageA not found | download the image bank (`blobMorphDownloadImages`); check the file names (section 1) |
| No Python interpreter with numpy, scipy, pillow and matplotlib was found | installation steps 2 and 3, or set `PythonExe` |
| The Python back end failed | read the Python messages printed above the error |
| Objects not recognised (Method `'preset'`) | images differ from renders of the reference objects; use `'auto'` or `'fit'`, or `'models'` with the scene files |

## Licence and credits

NGL BlobMorph (MATLAB and Python code, documentation): Copyright (c) 2026 Jesus J. Ballesteros,
MIT Licence (`LICENSE`).

| Material | Authors and source | Terms |
|---|---|---|
| Objects 1 and 2 (shapes, rendering set-up) | Zoccolan D, Oertelt N, DiCarlo JJ, Cox DD (2009); Cox lab, https://github.com/coxlab/povray_blobs | object parameters in `blobmorph/presets.py` and scene files in `tests/povray_reference/` transcribed from `code/Blobs_RatsD1D2/StimBlob_call_1.pov` and `StimBlob_call_2.pov`; centring and bounding box of `ResizeBlobRatStims_General.m` and `FindImageBoundingBox_call.m` reimplemented; renders of the objects in `examples/` and `tests/povray_reference/`; publications using them cite Zoccolan et al. (2009) |
| Image bank | Cox lab, https://github.com/coxlab/povray_blobs | no licence stated; not redistributed; downloaded by the user |
| Morph procedure | Rhee et al. (2025); Juliana Y. Rhee, https://github.com/julianarhee/morph-pov | MIT Licence, Copyright (c) 2025 julianarhee; morph plan (`make_pov_morphs.py`), equal-distance sampling (`utils/euclid.py`), centring and cropping (`matlab/ResizeBlobRatStims_General_morphs.m`) reimplemented, no code copied |
| Display constant (16.05 px per deg), morph level indices M0 to M106 (`tests/validate.py`) | Juliana Y. Rhee, https://github.com/julianarhee/rat-2p-area-characterizations (`analyze2p/objects/sim_utils.py`) | MIT Licence |
| Reference papers | PNAS (2009); Cell Reports (2025) | publisher terms; Rhee et al. (2025): CC BY-NC-ND 4.0; not redistributed |
| Rendering model | POV-Ray 3.7 (blob, camera and lighting model reimplemented; no POV-Ray code included) | POV-Ray is a trademark of Persistence of Vision Raytracer Pty. Ltd. |
| CMA-ES optimiser (image fitting) | Hansen N (2016). The CMA Evolution Strategy: A Tutorial. arXiv:1604.00772 | algorithm reimplemented |
| Python packages numpy, scipy, pillow, matplotlib | their authors | own licences; installed separately |

Publications using NGL BlobMorph cite the software, Zoccolan et al. (2009) for the objects and
Rhee et al. (2025) for the morphing procedure. Software: Ballesteros JJ (2026). NGL BlobMorph,
version 1.0.0 [software] (`CITATION.cff`).
