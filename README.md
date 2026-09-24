# NGL BlobMorph

MATLAB and Python tools that create a morph matrix (morph levels x stimulus sizes) between two
"blob" objects, as in Rhee et al. (2025), Fig. 1A and Fig. S4A. The objects are those of
Zoccolan et al. (2009).

Repository: https://github.com/JesusJBallesteros/NGL-BlobMorph. Author: Jesus J. Ballesteros.
Licence: MIT (`LICENSE`). Citation: `CITATION.cff`.

## Repository contents

```
NGL-BlobMorph/
    matlab/blobMorph_master.m           master script: all parameters as code, runs the morph
    matlab/blobMorph_live.m             live script: same parameters with controls, shows the results
    matlab/blobMorphMatrix.m            function called by both scripts
    matlab/blobMorphDownloadImages.m    downloads the image bank
    matlab/blobMorphPython.m            finds the Python interpreter
    matlab/blobMorphLoad.m              loads a results folder into MATLAB
    matlab/blobMorphReport.m            lists the files of a results folder
    notebooks/blobMorph_notebook.ipynb  Jupyter notebook: same parameters, shows the results
    blobmorph/                          Python back end and command-line tool
    examples/                           reference outputs
    tests/                              validation script, POV-Ray reference scenes and renders
    LICENSE, CITATION.cff, README.md, VALIDATION.md
```

Folders created locally and not part of the repository (`.gitignore`): `Images/` (image bank),
`References/` (reference papers), `results/` (default output folder).

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

The images are not distributed with NGL BlobMorph. Download into `Images/Blobs_TrainingRatsD1D2`:
- MATLAB: `blobMorphDownloadImages` (other folders of `images/`: `blobMorphDownloadImages('<folder>')`).
- Command terminal, in the `NGL-BlobMorph` folder: `python -m blobmorph.download`.
- Jupyter notebook: `DOWNLOAD = True` in section 0.
- git: `git clone https://github.com/coxlab/povray_blobs.git`, then copy
  `povray_blobs/images/Blobs_TrainingRatsD1D2/*.png` to `Images/Blobs_TrainingRatsD1D2/`.

Input images from other sources: grey renders (or white objects) on a black background, both
images of the same size. The two reference objects are recognised in full 4:3 POV-Ray frames of
any resolution and in windows of the 1100 x 825 frame (such as the image bank).

## Requirements

- Python 3.9 or later with numpy, scipy, pillow and matplotlib (all ways of use).
- MATLAB scripts: MATLAB R2021a or later, no toolbox. Controls of the live script: MATLAB R2025a
  or later.
- Jupyter notebook: JupyterLab or Jupyter Notebook.
- Internet access for the download of the image bank.
- Optional: POV-Ray 3.7 (renders the exported `.pov` scenes).
- About 5 MB of disk space per matrix of 9 levels x 5 sizes.

## Installation

1. Install Python from https://www.python.org/downloads/ (option "Add python.exe to PATH"), or
   use an Anaconda or Miniconda environment.
2. Install the packages in a command terminal (see Command terminal):
   ```
   python -m pip install numpy scipy pillow matplotlib
   ```
   For the Jupyter notebook, also:
   ```
   python -m pip install jupyterlab
   ```
3. Check the installation:
   ```
   python -c "import numpy, scipy, PIL, matplotlib; print('ok')"
   ```
4. Download the repository:
   ```
   git clone https://github.com/JesusJBallesteros/NGL-BlobMorph.git
   ```
   or, on the repository page, Code > Download ZIP, then extract the archive (folder
   `NGL-BlobMorph-main`).
5. Download the image bank (see Image bank), for example in a command terminal in the
   `NGL-BlobMorph` folder:
   ```
   python -m blobmorph.download
   ```
6. MATLAB with several Python installations: set `PythonExe` in section 10 of the scripts, or
   select the interpreter with `pyenv('Version', 'C:\path\to\python.exe')`.

## Creating a morph matrix

Four ways, with the same parameters and results:

| Way | File or command | Requirements |
|---|---|---|
| MATLAB master script | `matlab/blobMorph_master.m` | MATLAB, Python |
| MATLAB live script | `matlab/blobMorph_live.m` | MATLAB (controls: R2025a or later), Python |
| Jupyter notebook | `notebooks/blobMorph_notebook.ipynb` | Python, JupyterLab or Jupyter Notebook |
| Command terminal | `python -m blobmorph` | Python |

The default settings of the scripts and of the notebook reproduce Fig. S4A: 9 levels, sizes 10,
20, 30, 40 and 50 deg, level spacing `'uniform'`, luminance column `'schematic'`.

Running time on 8 cores:

| Case | Time |
|---|---|
| objects 1 and 2, `Sampling = 'uniform'` | 15 to 30 s |
| objects 1 and 2, `'arc'` or `'chord'` | about 2 min |
| objects 1 and 2, `'original'` | about 25 min |
| other objects (models fitted to the images) | about 25 min |

### MATLAB master script

1. Open `NGL-BlobMorph/matlab/blobMorph_master.m`.
2. Section 1: `ImageA` (level 0 %) and `ImageB` (level 100 %). Defaults: `Blob_N1_CamRot_y0.png`
   and `Blob_N2_CamRot_y0.png` of the image bank. Section 0: `OutputDir`, default
   `NGL-BlobMorph/results/morph_N1_N2`.
3. Sections 2 to 4: number of levels, sizes, spacing of the levels, display. Sections 5 to 10
   are needed only for other objects, special output options or performance settings.
4. Run the script (F5).
5. The results are in `OutputDir`. The folder content is printed at the end of the run.

### MATLAB live script

1. Open `NGL-BlobMorph/matlab/blobMorph_live.m` in the Live Editor (plain-text live script
   format).
2. Section 0: tick *Download image set* once if the image bank is missing.
3. Sections 1 to 10: set the parameters with the drop-down menus, check boxes, spinners, sliders,
   edit fields and file browsers.
4. Run the live script (Live Editor tab > Run). Section 11 checks the settings, section 12
   creates the morph matrix, sections 13 to 17 show the results and the location of the files.

MATLAB releases before R2025a open `blobMorph_live.m` as a plain script with the default values.
A binary live script: open `blobMorph_live.m` in the Live Editor, then Save As > Live Code File
(`*.mlx`).

### Jupyter notebook

1. Open a command terminal in the `NGL-BlobMorph` folder (see Command terminal) and start
   JupyterLab:
   ```
   python -m jupyter lab
   ```
   JupyterLab opens in the web browser.
2. Open `notebooks/blobMorph_notebook.ipynb` in the file browser on the left.
3. Section 0: `DOWNLOAD = True` once if the image bank is missing.
4. Sections 1 to 10: parameters, as Python variables (`NUM_LEVELS` for `NumLevels` of the MATLAB
   scripts).
5. Run > Run All Cells. Section 11 checks the settings, section 12 creates the morph matrix,
   sections 13 to 17 show the results and the location of the files.
6. Results: `results/morph_N1_N2` (`RESULTS_FOLDER`, section 0).

Other programs: Jupyter Notebook (`python -m jupyter notebook`); Visual Studio Code with the
Python and Jupyter extensions (open the notebook, select the Python interpreter as kernel, Run
All).

Notebook without the browser (results in `results/morph_N1_N2`, executed notebook in `results/`):
```
python -m jupyter nbconvert --to notebook --execute notebooks/blobMorph_notebook.ipynb --output-dir results
```

### Command terminal

A command terminal runs the Python tool, the MATLAB master script and the notebook without a
graphical interface.

1. Open a terminal:
   - Windows: Start menu > Terminal (or PowerShell, or Command Prompt); or, in File Explorer,
     right-click in the `NGL-BlobMorph` folder > Open in Terminal.
   - macOS: Applications > Utilities > Terminal.
   - Linux: terminal of the desktop environment.
   - Anaconda or Miniconda: Anaconda Prompt, then `conda activate <environment>`.
2. Go to the repository folder, for example:
   ```
   cd C:\Code\NGL-BlobMorph
   ```
   macOS and Linux, for example: `cd ~/NGL-BlobMorph`.
3. Download the image bank (once):
   ```
   python -m blobmorph.download
   ```
4. Create the morph matrix of Fig. S4A:
   ```
   python -m blobmorph Images/Blobs_TrainingRatsD1D2/Blob_N1_CamRot_y0.png Images/Blobs_TrainingRatsD1D2/Blob_N2_CamRot_y0.png --levels 9 --sizes 10 20 30 40 50 --sampling uniform --luminance-display schematic --out results/morph_N1_N2
   ```
   Paths with `/` work on Windows, macOS and Linux. The progress is printed in the terminal; the
   results folder has the content listed in Outputs.
5. All options:
   ```
   python -m blobmorph --help
   ```

Options of `python -m blobmorph` and parameters of the scripts:

| Option | Parameter | Default of the option |
|---|---|---|
| `IMAGE_A IMAGE_B` | `ImageA`, `ImageB` | none |
| `--out FOLDER` | `OutputDir` | `morph_matrix_output` |
| `--levels N` | `NumLevels` | 9 |
| `--sizes S1 S2 ...` | `Sizes` | 10 20 30 40 50 |
| `--sampling` | `Sampling` | `arc` |
| `--px-per-deg` | `PixelsPerDegree` | 16.05 |
| `--screen-px W H`, `--screen-cm`, `--distance-cm`, `--deg-mode` | `ScreenPixels`, `ScreenWidthCm`, `ViewingDistanceCm`, `DegreeMode` | 1920 1080, none, none, `mworks` |
| `--size-reference` | `SizeReference` | `crop_max` |
| `--display-gamma` | `DisplayGamma` | 2.2 |
| `--luminance-display` | `LuminanceDisplay` | `actual` |
| `--no-screens` | `SaveScreens = false` | screens saved |
| `--title TEXT` | `FigureTitle` | none |
| `--method`, `--model-a`, `--model-b`, `--setup` | `Method`, `ModelA`, `ModelB`, `Setup` | `auto`, none, none, `auto` |
| `--correspondence`, `--vanish` | `Correspondence`, `Vanish` | `match`, `fade` |
| `--center` | `Center` | `anchors` |
| `--inputs-as-anchors` | `UseInputsAsAnchors = true` | off |
| `--n-dense`, `--dense-scale`, `--processes` | `NumDense`, `DenseScale`, `Processes` | 201, 0.5, min(8, cores / 2) |
| `--quiet` | `Verbose = false` | progress printed |
| `--config FILE` | settings file | none |

`--config FILE`: JSON file with the option names of the Python back end (notebook, section 12,
`config`), for example `{"n_levels": 9, "sizes": [10, 20, 30, 40, 50], "sampling": "uniform"}`.
Parameters without a command-line option (`stim_pos_deg`, `crop_margin`, `antialias`, `fit`,
...) are set in this file. Options given on the command line replace the values of the file.

Other commands, in the `NGL-BlobMorph` folder:
```
python -m blobmorph.download [IMAGE_SET] [--dest FOLDER]
python -m blobmorph.povray OUTPUT_DIR
python tests/validate.py
```
`blobmorph.download`: image bank. `blobmorph.povray`: renders `OUTPUT_DIR/models/morphLL.pov`
with POV-Ray. `tests/validate.py`: validation (VALIDATION.md).

MATLAB master script, with the settings of the script (MATLAB on the system path; results in
`OutputDir`):
```
matlab -batch "run('matlab/blobMorph_master.m')"
```

Jupyter notebook: see Jupyter notebook, `nbconvert` command.

## Parameters

Sections of `blobMorph_master.m`, `blobMorph_live.m` and `blobMorph_notebook.ipynb`. Each
parameter is described in the scripts with examples from the project data.

| Section | Parameter | Default | Values |
|---|---|---|---|
| 0 | `OutputDir` | `results/morph_N1_N2` | folder |
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
| `figures/morph_matrix.png`, `.pdf` | morph matrix: sizes (rows, largest on top) x morph levels (columns), luminance column |
| `figures/morph_matrix_panel.png` | morph matrix without labels |
| `figures/distance_profile.png` | Euclidean pixel distance along the morph and between successive levels |
| `stimuli/morphLL_levelPPP.PP_sizeSSS.S.png` | stimulus of level LL (PPP.PP %) at size SSS.S deg, cropped |
| `screens/morphLL_levelPPP.PP_sizeSSS.S.png` | same stimulus on a full screen (`ScreenPixels`) |
| `screens/fullfield_luminance_sizeSSS.S.png` | full-field luminance control for each size |
| `frames/morphLL_levelPPP.PP.png` | frame of each level, same size as the input images |
| `models/morphLL.json`, `.pov` | 3-D model and POV-Ray scene of each level |
| `models/fitted_A.json`, `fitted_B.json` | fitted models with their rendering set-up (when models are fitted); reusable as `ModelA`, `ModelB` without refitting |
| `manifest.csv` | one row per stimulus: level index, morph level (%), morph parameter t, size (deg), files, size in px, full-field grey level |
| `manifest.json` | all settings and results |

MATLAB structure `R` (workspace after the run, or `R = blobMorphLoad(OutputDir)`):
`R.levels`, `R.t`, `R.sizes`, `R.stimuli{size, level}` (uint8 images), `R.files`, `R.screens`,
`R.luminance`, `R.lumPerSize`, `R.matrix`, `R.figureFile`, `R.manifest`. Python and notebook:
`manifest = blobmorph.pipeline.run(config)`, the content of `manifest.json`.

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

## Reference outputs

Figures, manifests and fitted models of two runs. Stimuli, screens, frames and per-level models
are not included.

| Folder | Content |
|---|---|
| `examples/reproduction_FigS4A` | `Blob_N1_CamRot_y0.png` and `Blob_N2_CamRot_y0.png` with the default settings |
| `examples/fitted_from_images` | the same images with `Method = 'fit'`; fitted models in `models/` |

Complete output folders, in a command terminal in the `NGL-BlobMorph` folder (image bank
downloaded):
```
python -m blobmorph Images/Blobs_TrainingRatsD1D2/Blob_N1_CamRot_y0.png Images/Blobs_TrainingRatsD1D2/Blob_N2_CamRot_y0.png --levels 9 --sizes 10 20 30 40 50 --sampling uniform --luminance-display schematic --out results/reproduction_FigS4A
python -m blobmorph Images/Blobs_TrainingRatsD1D2/Blob_N1_CamRot_y0.png Images/Blobs_TrainingRatsD1D2/Blob_N2_CamRot_y0.png --method models --model-a examples/fitted_from_images/models/fitted_A.json --model-b examples/fitted_from_images/models/fitted_B.json --levels 9 --sizes 10 20 30 40 50 --sampling uniform --luminance-display schematic --out results/fitted_from_images
```
Running time: about 15 s each. MATLAB: master script with the default settings (first
command), or with `Method = 'models'` and the fitted models as `ModelA` and `ModelB` (section 5,
second command). Replacing `--method models --model-a ... --model-b ...` by `--method fit`
repeats the fit (about 25 min).

## Validation

`VALIDATION.md` lists the comparisons with POV-Ray, with the image bank and with Fig. S4A.
`python tests/validate.py` repeats them (Fig. S4A: option `--figure`).

## Troubleshooting

| Message | Action |
|---|---|
| ImageA not found | download the image bank (see Image bank); check the file names (section 1) |
| No Python interpreter with numpy, scipy, pillow and matplotlib was found | installation steps 2 and 3, or set `PythonExe` |
| The Python back end failed | read the Python messages printed above the error |
| Objects not recognised (Method `'preset'`) | images differ from renders of the reference objects; use `'auto'` or `'fit'`, or `'models'` with the scene files |
| `No module named blobmorph` | run the command, or start Jupyter, in the `NGL-BlobMorph` folder |
| `'python' is not recognized` (Windows) | reinstall Python with "Add python.exe to PATH", or use `py` instead of `python` |
| `No module named jupyter` | `python -m pip install jupyterlab` |
| `'matlab' is not recognized` | add the `bin` folder of MATLAB to the system path, or give the full path, e.g. `"C:\Program Files\MATLAB\R2026a\bin\matlab.exe"` |

## Licence and credits

NGL BlobMorph (MATLAB and Python code, notebook, documentation): Copyright (c) 2026 Jesus J.
Ballesteros, MIT Licence (`LICENSE`).

| Material | Authors and source | Terms |
|---|---|---|
| Objects 1 and 2 (shapes, rendering set-up) | Zoccolan D, Oertelt N, DiCarlo JJ, Cox DD (2009); Cox lab, https://github.com/coxlab/povray_blobs | object parameters in `blobmorph/presets.py` and scene files in `tests/povray_reference/` transcribed from `code/Blobs_RatsD1D2/StimBlob_call_1.pov` and `StimBlob_call_2.pov`; centring and bounding box of `ResizeBlobRatStims_General.m` and `FindImageBoundingBox_call.m` reimplemented; renders of the objects in `examples/` and `tests/povray_reference/`; publications using them cite Zoccolan et al. (2009) |
| Image bank | Cox lab, https://github.com/coxlab/povray_blobs | no licence stated; not redistributed; downloaded by the user |
| Morph procedure | Rhee et al. (2025); Juliana Y. Rhee, https://github.com/julianarhee/morph-pov | MIT Licence, Copyright (c) 2025 julianarhee; morph plan (`make_pov_morphs.py`), equal-distance sampling (`utils/euclid.py`), centring and cropping (`matlab/ResizeBlobRatStims_General_morphs.m`) reimplemented, no code copied |
| Display constant (16.05 px per deg), morph level indices M0 to M106 (`tests/validate.py`) | Juliana Y. Rhee, https://github.com/julianarhee/rat-2p-area-characterizations (`analyze2p/objects/sim_utils.py`) | MIT Licence |
| Reference papers | PNAS (2009); Cell Reports (2025) | publisher terms; Rhee et al. (2025): CC BY-NC-ND 4.0; not redistributed |
| Rendering model | POV-Ray 3.7 (blob, camera and lighting model reimplemented; no POV-Ray code included) | POV-Ray is a trademark of Persistence of Vision Raytracer Pty. Ltd. |
| CMA-ES optimiser (image fitting) | Hansen N (2016). The CMA Evolution Strategy: A Tutorial. arXiv:1604.00772 | algorithm reimplemented |
| Python packages numpy, scipy, pillow, matplotlib, Jupyter | their authors | own licences; installed separately |

Publications using NGL BlobMorph cite the software, Zoccolan et al. (2009) for the objects and
Rhee et al. (2025) for the morphing procedure. Software: Ballesteros JJ (2026). NGL BlobMorph,
version 1.0.0 [software]. https://github.com/JesusJBallesteros/NGL-BlobMorph (`CITATION.cff`).
