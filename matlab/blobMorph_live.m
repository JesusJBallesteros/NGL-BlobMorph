%[text] # NGL BlobMorph live script
%[text] Creates a morph matrix (morph levels x stimulus sizes) between two blob objects, following Rhee et al. (2025, *Cell Reports*, Fig. 1A and Fig. S4A) and Zoccolan et al. (2009, *PNAS*). The parameters are set with the controls; `blobMorph_master.m` holds the same parameters as code.
%[text] 1. Section 0: image bank. Tick *Download image set* once to download the images.
%[text] 2. Sections 1 to 10: parameters. Section 1 is required; the other sections have working defaults.
%[text] 3. Section 11: checks of the settings.
%[text] 4. Section 12: morph. Run the whole script (Live Editor tab > Run), or sections 11 to 17 in order.
%[text] 5. Sections 13 to 17: results and location of the files. \
%[text] Controls require MATLAB R2025a or later; earlier releases run the script with the default values. A control change runs its own section.
%[text] Author: Jesus J. Ballesteros. NGL BlobMorph, MIT Licence (see `LICENSE`).
%%
%[text] ## 0. Image bank and folders
%[text] Image bank: folder `images` of the repository https://github.com/coxlab/povray_blobs (Cox lab; not distributed with NGL BlobMorph). *Download image set* saves the images of *Image set* in `Images\<image set>` of the NGL-BlobMorph folder. Results are written to `results\<results folder>`.
ToolboxDir = fileparts(fileparts(mfilename('fullpath')));  % NGL-BlobMorph folder
if ~isfolder(fullfile(ToolboxDir, 'blobmorph'))
    ToolboxDir = fileparts(fileparts(which('blobMorphMatrix')));
end
assert(isfolder(fullfile(ToolboxDir, 'blobmorph')), ...
    'NGL-BlobMorph folder not found: open this script from NGL-BlobMorph\matlab.');
addpath(fullfile(ToolboxDir, 'matlab'));
ImageSet = 'Blobs_TrainingRatsD1D2'; %[control:editfield:0b11]{"position":[12,36]}
DownloadImageSet = false; %[control:checkbox:0b12]{"position":[20,25]}
ResultsFolder = 'morph_N1_N2'; %[control:editfield:0b13]{"position":[17,30]}
DataDir = fullfile(ToolboxDir, 'Images', ImageSet);
OutputDir = fullfile(ToolboxDir, 'results', ResultsFolder);
if DownloadImageSet
    blobMorphDownloadImages(ImageSet);
end
if isfolder(DataDir)
    fprintf('Image bank: %s (%d images)\nResults: %s\n', DataDir, ...
        numel(dir(fullfile(DataDir, '*.png'))), OutputDir);
else
    fprintf('Image bank not found: %s\nTick Download image set.\n', DataDir);
end
%%
%[text] ## 1. Input images (required)
%[text] *Object A*: morph level 0 %. *Object B*: morph level 100 %. *Rotation*: view of both objects, rotation about the vertical axis (image bank: -90 to 90 deg in steps of 15 deg; 0 is the default view of Zoccolan et al. 2009, Fig. 1A). A file chosen in *Other image A* or *Other image B* replaces the selection: grayscale renders on a black background, both of the same size. With *Method* = models (section 5) no images are needed.
ObjectA = 'Blob_N1'; %[control:dropdown:0b14]{"position":[11,20]}
ObjectB = 'Blob_N2'; %[control:dropdown:0b15]{"position":[11,20]}
Rotation = 0; %[control:slider:0b16]{"position":[12,13]}
OtherImageA = ""; %[control:filebrowser:0b17]{"position":[15,17]}
OtherImageB = ""; %[control:filebrowser:0b18]{"position":[15,17]}
ImageA = fullfile(DataDir, sprintf('%s_CamRot_y%d.png', ObjectA, Rotation));
ImageB = fullfile(DataDir, sprintf('%s_CamRot_y%d.png', ObjectB, Rotation));
if strlength(OtherImageA) > 0, ImageA = char(OtherImageA); end
if strlength(OtherImageB) > 0, ImageB = char(OtherImageB); end
fprintf('ImageA: %s\nImageB: %s\n', ImageA, ImageB);
%%
%[text] ## 2. Morph matrix
%[text] *Morph levels*: both objects included; 9 in Fig. S4A, 22 in the behavioural morph set. *Sizes*: degrees of visual angle; `[10 20 30 40 50]` in Fig. S4A, `[15 20 25 30 35 40]` in Zoccolan et al. (2009), Fig. 2.
%[text] *Level spacing*:
%[text] - uniform: equal steps of the morph parameter (levels of Fig. S4A)
%[text] - arc: equal pixel-space Euclidean distance along the morph (Rhee et al. 2025, Methods)
%[text] - chord: equal Euclidean distance between successive chosen levels
%[text] - original: procedure of julianarhee/morph-pov, 2000 morphs, about 25 min \
NumLevels = 9; %[control:spinner:0b19]{"position":[13,14]}
Sizes = [10 20 30 40 50]; %[control:editfield:0b1a]{"position":[9,25]}
Sampling = 'uniform'; %[control:dropdown:0b1b]{"position":[12,21]}
%%
%[text] ## 3. Display: degrees to pixels
%[text] *Definition*: pixels per degree, or screen geometry (width in pixels and cm, viewing distance). Examples: 16.05 px per deg (two-photon imaging display, Rhee et al. 2025); Samsung SyncMaster 940BX, 1280 x 1024 px, 37.6 cm wide, eyes at 25 cm (Zoccolan et al. 2009). *Conversion* (screen geometry): mworks, linear in degrees over the whole screen; tangent, exact visual angle at the screen centre; linear, small-angle approximation. *Screen* also sets the size of the full-screen images. *Stimulus x, y*: centre on the screen images, degrees from the screen centre. *Size reference*: dimension that spans the size (longest side of the common crop of all levels; its width or height; or each object's own bounding box).
DisplayDefinition = 'ppd'; %[control:dropdown:0b1c]{"position":[21,26]}
PixelsPerDegree = 16.05; %[control:editfield:0b1d]{"position":[19,24]}
ScreenWidthPx = 1920; %[control:spinner:0b1e]{"position":[17,21]}
ScreenHeightPx = 1080; %[control:spinner:0b1f]{"position":[18,22]}
ScreenWidthCm = 37.6; %[control:editfield:0b20]{"position":[17,21]}
ViewingDistanceCm = 25; %[control:editfield:0b21]{"position":[21,23]}
DegreeMode = 'mworks'; %[control:dropdown:0b22]{"position":[14,22]}
StimulusX = 0; %[control:spinner:0b23]{"position":[13,14]}
StimulusY = 0; %[control:spinner:0b24]{"position":[13,14]}
SizeReference = 'crop_max'; %[control:dropdown:0b25]{"position":[17,27]}
ScreenPixels = [ScreenWidthPx ScreenHeightPx];
StimulusPositionDeg = [StimulusX StimulusY];
if strcmp(DisplayDefinition, 'ppd')
    ScreenWidthCm = [];
    ViewingDistanceCm = [];
else
    PixelsPerDegree = [];
end
%%
%[text] ## 4. Luminance controls and figure
%[text] *Display gamma*: gamma of the display for the luminance-matched full-field grey levels (1 for a linearised display). *Luminance column*: computed full-field levels, or 255 x size / largest size as drawn in Fig. S4A.
DisplayGamma = 2.2; %[control:slider:0b26]{"position":[16,19]}
SaveScreens = true; %[control:checkbox:0b27]{"position":[15,19]}
LuminanceDisplay = 'schematic'; %[control:dropdown:0b28]{"position":[20,31]}
FigureTitle = ''; %[control:editfield:0b29]{"position":[15,17]}
%%
%[text] ## 5. Object models
%[text] *Method*:
%[text] - auto: recognise the two reference objects (Zoccolan et al. 2009), otherwise fit models to the images
%[text] - preset: reference objects only
%[text] - fit: blob models fitted to the images (about 11 min per image)
%[text] - models: *Model A* and *Model B* (POV-Ray `.pov` scene or `.json` model) \
%[text] Model examples: `tests\povray_reference\obj1_cam11_v36.pov` and `obj2_cam11_v36.pov` (scene files of the reference objects); `examples\fitted_from_images\models\fitted_A.json` and `fitted_B.json` (models fitted in a previous run). *Rendering set-up* for fitted objects and model files: auto (fitted objects: camera z = -11, tone curve zoccolan, antialiasing as the input images; fitted models `.json`: set-up stored in the file; `.pov` files: camera of the scene file, tone curve calibrated on the images, linear without images), provided (camera z = -11, tone curve zoccolan), zoccolan2009 (camera z = -10, linear output), rhee2025 (camera z = -10, sRGB output, no antialiasing). `PovDeclare`: values of identifiers left free in `.pov` files, e.g. `struct('obj_pos_z', 6)`.
Method = 'auto'; %[control:dropdown:0b2a]{"position":[10,16]}
ModelA = ""; %[control:filebrowser:0b2b]{"position":[10,12]}
ModelB = ""; %[control:filebrowser:0b2c]{"position":[10,12]}
Setup = 'auto'; %[control:dropdown:0b2d]{"position":[9,15]}
PovDeclare = struct();
ModelA = char(ModelA);
ModelB = char(ModelB);
%%
%[text] ## 6. Correspondence between object parts
%[text] Objects other than the reference pair. *Correspondence*: match, matched parts are interpolated and the others fade; crossfade, all parts of A fade out while all parts of B fade in; index, part i of A becomes part i of B. *Parts without partner*: fade (strength to 0) or shrink (radius to 0). *Interpolation*: pov, linear on the POV-Ray numbers; geometric, centre, semi-axes and orientation of each ellipsoid; auto, geometric for fitted models.
Correspondence = 'match'; %[control:dropdown:0b2e]{"position":[18,25]}
Vanish = 'fade'; %[control:dropdown:0b2f]{"position":[10,16]}
Interpolation = 'auto'; %[control:dropdown:0b30]{"position":[17,23]}
%%
%[text] ## 7. Image fitting
%[text] Used with *Method* = fit, or auto when the objects are not recognised. `FitStages`: one row per stage, [resolution factor, supersampling, maximum generations, initial step].
FitSymmetric = 'auto'; %[control:dropdown:0b31]{"position":[16,22]}
FitMaxComponents = 4; %[control:spinner:0b32]{"position":[20,21]}
FitMaxExtra = 2; %[control:spinner:0b33]{"position":[15,16]}
FitRestarts = 1; %[control:spinner:0b34]{"position":[15,16]}
FitPopulation = 16; %[control:spinner:0b35]{"position":[17,19]}
FitSeed = 0; %[control:spinner:0b36]{"position":[11,12]}
FitStages = [0.15 2 160 1.0
             0.30 2  70 0.3
             0.50 1  40 0.1];
%%
%[text] ## 8. Post-processing of the rendered frames
%[text] *Input images as anchors*: levels 0 % and 100 % are the input images instead of renders. *Centring*: joint bounding box of both objects centred in the frame. *Crop margin*: pixels around the joint bounding box of all levels. *Antialiasing* auto: as the input images.
UseInputsAsAnchors = false; %[control:checkbox:0b37]{"position":[22,27]}
Center = 'anchors'; %[control:dropdown:0b38]{"position":[10,19]}
CenterHorizontal = true; %[control:checkbox:0b39]{"position":[20,24]}
CropMargin = 2; %[control:spinner:0b3a]{"position":[14,15]}
Antialias = 'auto'; %[control:dropdown:0b3b]{"position":[13,19]}
SaveFrames = true; %[control:checkbox:0b3c]{"position":[14,18]}
SavePov = true; %[control:checkbox:0b3d]{"position":[11,15]}
LuminanceColumn = true; %[control:checkbox:0b3e]{"position":[19,23]}
%%
%[text] ## 9. Performance
%[text] *Dense continuum*: morphs rendered to measure pixel distances (0: 201; 2002 for original). *Processes*: parallel Python processes (0: min(8, number of cores / 2)).
NumDense = 0; %[control:spinner:0b3f]{"position":[12,13]}
DenseScale = 0.5; %[control:slider:0b40]{"position":[14,17]}
DenseSupersample = 2; %[control:spinner:0b41]{"position":[20,21]}
Processes = 0; %[control:spinner:0b42]{"position":[13,14]}
%%
%[text] ## 10. Environment
%[text] *Python interpreter*: empty selects the first interpreter with numpy, scipy, pillow and matplotlib among pyenv, python, python3 and py -3.
PythonExe = ""; %[control:filebrowser:0b43]{"position":[13,15]}
Verbose = false; %[control:checkbox:0b44]{"position":[11,16]}
PythonExe = char(PythonExe);
%%
%[text] ## 11. Checks
%[text] Lists the settings and stops with a message when an input is missing or a value is out of range.
problems = {};
if ~strcmpi(Method, 'models')
    if ~isfile(ImageA), problems{end+1} = sprintf('ImageA not found: %s (section 0, Download image set)', ImageA); end
    if ~isfile(ImageB), problems{end+1} = sprintf('ImageB not found: %s', ImageB); end
    if isfile(ImageA) && isfile(ImageB)
        ia = imfinfo(ImageA);
        ib = imfinfo(ImageB);
        if ia.Width ~= ib.Width || ia.Height ~= ib.Height
            problems{end+1} = 'ImageA and ImageB differ in size';
        end
    end
elseif ~isfile(ModelA) || ~isfile(ModelB)
    problems{end+1} = 'Method models: select Model A and Model B (section 5)';
end
if ~isnumeric(Sizes) || isempty(Sizes) || any(Sizes(:) <= 0)
    problems{end+1} = 'Sizes: positive numbers in degrees, e.g. [10 20 30 40 50]';
end
if strcmp(DisplayDefinition, 'ppd') && ~(PixelsPerDegree > 0)
    problems{end+1} = 'Pixels per degree must be positive';
end
if strcmp(DisplayDefinition, 'geometry') && ~(ScreenWidthCm > 0 && ViewingDistanceCm > 0)
    problems{end+1} = 'Screen width and viewing distance must be positive';
end
try
    [pyCmd, pyInfo] = blobMorphPython(PythonExe);
catch err
    pyCmd = '';
    pyInfo = '';
    problems{end+1} = err.message;
end
fprintf('Images:      %s\n             %s\n', ImageA, ImageB);
fprintf('Levels:      %d (%s)\n', NumLevels, Sampling);
fprintf('Sizes (deg): %s\n', mat2str(Sizes));
fprintf('Method:      %s\n', Method);
fprintf('Python:      %s\n             %s\n', pyCmd, pyInfo);
fprintf('Results:     %s\n', OutputDir);
if isempty(problems)
    fprintf('Settings OK.\n');
else
    error('blobMorph:settings', '%s', strjoin(problems, newline));
end
%%
%[text] ## 12. Morph
%[text] Creates the morph matrix. Duration on 8 cores: 15 to 30 s (reference objects, uniform); about 2 min (arc or chord); about 25 min (original, or objects fitted to the images).
args = {'NumLevels', NumLevels, 'Sizes', Sizes, 'Sampling', Sampling, ...
    'ScreenPixels', ScreenPixels, 'DegreeMode', DegreeMode, ...
    'StimulusPositionDeg', StimulusPositionDeg, 'SizeReference', SizeReference, ...
    'DisplayGamma', DisplayGamma, 'SaveScreens', SaveScreens, ...
    'LuminanceDisplay', LuminanceDisplay, 'Title', FigureTitle, 'Method', Method, ...
    'Setup', Setup, 'Correspondence', Correspondence, 'Vanish', Vanish, ...
    'OutputDir', OutputDir, 'Python', PythonExe, 'Verbose', Verbose, 'ShowFigure', false};
if ~isempty(PixelsPerDegree),   args = [args, {'PixelsPerDegree', PixelsPerDegree}]; end
if ~isempty(ScreenWidthCm),     args = [args, {'ScreenWidthCm', ScreenWidthCm}]; end
if ~isempty(ViewingDistanceCm), args = [args, {'ViewingDistanceCm', ViewingDistanceCm}]; end
if strcmpi(Method, 'models'),   args = [args, {'ModelA', ModelA, 'ModelB', ModelB}]; end
if NumDense > 0,                args = [args, {'NumDense', NumDense}]; end
if Processes > 0,               args = [args, {'Processes', Processes}]; end
advanced = struct('interpolation', Interpolation, ...
    'use_inputs_as_anchors', UseInputsAsAnchors, 'center', Center, ...
    'center_horizontal', CenterHorizontal, 'crop_margin', CropMargin, ...
    'antialias', Antialias, 'save_frames', SaveFrames, 'save_pov', SavePov, ...
    'luminance_column', LuminanceColumn, 'dense_scale', DenseScale, ...
    'dense_supersample', DenseSupersample, ...
    'fit', struct('symmetric', FitSymmetric, 'max_components', FitMaxComponents, ...
                  'max_extra', FitMaxExtra, 'restarts', FitRestarts, ...
                  'popsize', FitPopulation, 'seed', FitSeed, 'stages', FitStages));
if ~isempty(fieldnames(PovDeclare)), advanced.pov_declare = PovDeclare; end
args = [args, {'Advanced', advanced}];
if strcmpi(Method, 'models') && ~isfile(ImageA), ImageA = ''; ImageB = ''; end
R = blobMorphMatrix(ImageA, ImageB, args{:});
%%
%[text] ## 13. Results: morph matrix
%[text] File: `figures\morph_matrix.png` (also `morph_matrix.pdf`; without labels: `morph_matrix_panel.png`) in the results folder.
panel = imread(fullfile(R.outputDir, 'figures', 'morph_matrix_panel.png'));
cellW = size(panel, 2) / numel(R.levels);
cellH = size(panel, 1) / numel(R.sizes);
figure('Color', 'w', 'Position', [50 50 1300 460]);
image(repmat(panel, [1 1 3]));
axis image;
set(gca, 'XTick', ((1:numel(R.levels)) - 0.5) * cellW, 'XTickLabel', string(R.levels), ...
    'YTick', ((1:numel(R.sizes)) - 0.5) * cellH, 'YTickLabel', string(sort(R.sizes, 'descend')), ...
    'TickLength', [0 0]);
xlabel('morph level (%)');
ylabel('size (deg)');
%%
%[text] ## 14. Results: all morph levels at the largest size
%[text] Files: `stimuli\morphLL_levelPPP.PP_sizeSSS.S.png` (LL: level index, PPP.PP: morph level in %, SSS.S: size in degrees). Full-screen versions: `screens\`.
iSize = find(R.sizes == max(R.sizes), 1);
figure('Color', 'k', 'Position', [50 50 1300 260]);
imshow(cat(2, R.stimuli{iSize, :}), 'Border', 'tight');
title(sprintf('%g deg; morph levels %s %%', R.sizes(iSize), mat2str(R.levels, 3)), 'Color', 'w');
%%
%[text] ## 15. Results: middle morph level at all sizes
iLevel = ceil(numel(R.levels) / 2);
column = R.stimuli(:, iLevel)';
h = max(cellfun(@(x) size(x, 1), column));
padded = cellfun(@(x) [zeros(floor((h - size(x, 1)) / 2), size(x, 2), 'uint8'); x; ...
    zeros(ceil((h - size(x, 1)) / 2), size(x, 2), 'uint8')], column, 'UniformOutput', false);
figure('Color', 'k', 'Position', [50 50 1300 330]);
imshow(cat(2, padded{:}), 'Border', 'tight');
title(sprintf('morph level %g %%; sizes %s deg', R.levels(iLevel), mat2str(R.sizes)), 'Color', 'w');
%%
%[text] ## 16. Results: pixel distance between successive morph levels
%[text] Euclidean distance between the cropped full-size frames of successive levels. File: `figures\distance_profile.png`, which also shows the cumulative distance along the dense continuum (level spacing arc, chord or original).
d = R.manifest.chord_distances_full_res(:)';
figure('Color', 'w', 'Position', [50 50 1100 380]);
bar(d, 'FaceColor', [0.5 0.5 0.5]);
set(gca, 'XTick', 1:numel(d), 'XTickLabel', compose('%g-%g', R.levels(1:end-1)', R.levels(2:end)'));
xlabel('morph levels (%)');
ylabel('Euclidean distance');
box off;
%%
%[text] ## 17. Results: list of stimuli and location of the files
%[text] `manifest.csv`: one row per stimulus (morph level, morph parameter t, size, file names, size in pixels, luminance-matched full-field grey level). `manifest.json`: all settings and results.
StimulusTable = blobMorphReport(R);
head(StimulusTable, 10)

%[appendix]{"version":"1.0"}
%---
%[metadata:view]
%   data: {"layout":"inline"}
%---
%[control:editfield:0b11]
%   data: {"defaultValue":"'Blobs_TrainingRatsD1D2'","label":"Image set","run":"Section","valueType":"Char"}
%---
%[control:checkbox:0b12]
%   data: {"defaultValue":false,"label":"Download image set","run":"Section"}
%---
%[control:editfield:0b13]
%   data: {"defaultValue":"'morph_N1_N2'","label":"Results folder","run":"Section","valueType":"Char"}
%---
%[control:dropdown:0b14]
%   data: {"defaultValue":"'Blob_N1'","itemLabels":["object 1","object 2"],"items":["'Blob_N1'","'Blob_N2'"],"label":"Object A","run":"Section"}
%---
%[control:dropdown:0b15]
%   data: {"defaultValue":"'Blob_N2'","itemLabels":["object 1","object 2"],"items":["'Blob_N1'","'Blob_N2'"],"label":"Object B","run":"Section"}
%---
%[control:slider:0b16]
%   data: {"defaultValue":0,"label":"Rotation (deg)","max":90,"min":-90,"run":"Section","runOn":"ValueChanged","step":15}
%---
%[control:filebrowser:0b17]
%   data: {"browserType":"File","defaultValue":"\"\"","label":"Other image A","run":"Section"}
%---
%[control:filebrowser:0b18]
%   data: {"browserType":"File","defaultValue":"\"\"","label":"Other image B","run":"Section"}
%---
%[control:spinner:0b19]
%   data: {"defaultValue":9,"label":"Morph levels","max":101,"min":2,"run":"Section","runOn":"ValueChanged","step":1}
%---
%[control:editfield:0b1a]
%   data: {"defaultValue":"[10 20 30 40 50]","label":"Sizes (deg)","run":"Section","valueType":"MATLAB code"}
%---
%[control:dropdown:0b1b]
%   data: {"defaultValue":"'uniform'","itemLabels":["uniform","arc","chord","original"],"items":["'uniform'","'arc'","'chord'","'original'"],"label":"Level spacing","run":"Section"}
%---
%[control:dropdown:0b1c]
%   data: {"defaultValue":"'ppd'","itemLabels":["pixels per degree","screen geometry"],"items":["'ppd'","'geometry'"],"label":"Definition","run":"Section"}
%---
%[control:editfield:0b1d]
%   data: {"defaultValue":16.05,"label":"Pixels per degree","run":"Section","valueType":"Double"}
%---
%[control:spinner:0b1e]
%   data: {"defaultValue":1920,"label":"Screen width (px)","max":7680,"min":320,"run":"Section","runOn":"ValueChanged","step":1}
%---
%[control:spinner:0b1f]
%   data: {"defaultValue":1080,"label":"Screen height (px)","max":4320,"min":240,"run":"Section","runOn":"ValueChanged","step":1}
%---
%[control:editfield:0b20]
%   data: {"defaultValue":37.6,"label":"Screen width (cm)","run":"Section","valueType":"Double"}
%---
%[control:editfield:0b21]
%   data: {"defaultValue":25.0,"label":"Viewing distance (cm)","run":"Section","valueType":"Double"}
%---
%[control:dropdown:0b22]
%   data: {"defaultValue":"'mworks'","itemLabels":["mworks","tangent","linear"],"items":["'mworks'","'tangent'","'linear'"],"label":"Conversion","run":"Section"}
%---
%[control:spinner:0b23]
%   data: {"defaultValue":0,"label":"Stimulus x (deg)","max":90,"min":-90,"run":"Section","runOn":"ValueChanged","step":0.5}
%---
%[control:spinner:0b24]
%   data: {"defaultValue":0,"label":"Stimulus y (deg)","max":90,"min":-90,"run":"Section","runOn":"ValueChanged","step":0.5}
%---
%[control:dropdown:0b25]
%   data: {"defaultValue":"'crop_max'","itemLabels":["longest side of the common crop","width of the common crop","height of the common crop","longest side of each object"],"items":["'crop_max'","'crop_width'","'crop_height'","'object_max'"],"label":"Size reference","run":"Section"}
%---
%[control:slider:0b26]
%   data: {"defaultValue":2.2,"label":"Display gamma","max":3,"min":1,"run":"Section","runOn":"ValueChanged","step":0.1}
%---
%[control:checkbox:0b27]
%   data: {"defaultValue":true,"label":"Save full-screen images","run":"Section"}
%---
%[control:dropdown:0b28]
%   data: {"defaultValue":"'schematic'","itemLabels":["actual","schematic"],"items":["'actual'","'schematic'"],"label":"Luminance column","run":"Section"}
%---
%[control:editfield:0b29]
%   data: {"defaultValue":"''","label":"Figure title","run":"Section","valueType":"Char"}
%---
%[control:dropdown:0b2a]
%   data: {"defaultValue":"'auto'","itemLabels":["auto","preset","fit","models"],"items":["'auto'","'preset'","'fit'","'models'"],"label":"Method","run":"Section"}
%---
%[control:filebrowser:0b2b]
%   data: {"browserType":"File","defaultValue":"\"\"","label":"Model A","run":"Section"}
%---
%[control:filebrowser:0b2c]
%   data: {"browserType":"File","defaultValue":"\"\"","label":"Model B","run":"Section"}
%---
%[control:dropdown:0b2d]
%   data: {"defaultValue":"'auto'","itemLabels":["auto","provided","zoccolan2009","rhee2025"],"items":["'auto'","'provided'","'zoccolan2009'","'rhee2025'"],"label":"Rendering set-up","run":"Section"}
%---
%[control:dropdown:0b2e]
%   data: {"defaultValue":"'match'","itemLabels":["match","crossfade","index"],"items":["'match'","'crossfade'","'index'"],"label":"Correspondence","run":"Section"}
%---
%[control:dropdown:0b2f]
%   data: {"defaultValue":"'fade'","itemLabels":["fade","shrink"],"items":["'fade'","'shrink'"],"label":"Parts without partner","run":"Section"}
%---
%[control:dropdown:0b30]
%   data: {"defaultValue":"'auto'","itemLabels":["auto","pov","geometric"],"items":["'auto'","'pov'","'geometric'"],"label":"Interpolation","run":"Section"}
%---
%[control:dropdown:0b31]
%   data: {"defaultValue":"'auto'","itemLabels":["auto","yes","no"],"items":["'auto'","true","false"],"label":"Left-right symmetric","run":"Section"}
%---
%[control:spinner:0b32]
%   data: {"defaultValue":4,"label":"Lobes from the silhouette (max)","max":8,"min":1,"run":"Section","runOn":"ValueChanged","step":1}
%---
%[control:spinner:0b33]
%   data: {"defaultValue":2,"label":"Parts added inside the silhouette (max)","max":4,"min":0,"run":"Section","runOn":"ValueChanged","step":1}
%---
%[control:spinner:0b34]
%   data: {"defaultValue":1,"label":"Runs of the first stage","max":5,"min":1,"run":"Section","runOn":"ValueChanged","step":1}
%---
%[control:spinner:0b35]
%   data: {"defaultValue":16,"label":"CMA-ES population","max":64,"min":8,"run":"Section","runOn":"ValueChanged","step":4}
%---
%[control:spinner:0b36]
%   data: {"defaultValue":0,"label":"Random seed","max":10000,"min":0,"run":"Section","runOn":"ValueChanged","step":1}
%---
%[control:checkbox:0b37]
%   data: {"defaultValue":false,"label":"Input images as anchors","run":"Section"}
%---
%[control:dropdown:0b38]
%   data: {"defaultValue":"'anchors'","itemLabels":["anchors","none"],"items":["'anchors'","'none'"],"label":"Centring","run":"Section"}
%---
%[control:checkbox:0b39]
%   data: {"defaultValue":true,"label":"Centre horizontally","run":"Section"}
%---
%[control:spinner:0b3a]
%   data: {"defaultValue":2,"label":"Crop margin (px)","max":100,"min":0,"run":"Section","runOn":"ValueChanged","step":1}
%---
%[control:dropdown:0b3b]
%   data: {"defaultValue":"'auto'","itemLabels":["auto","on","off"],"items":["'auto'","true","false"],"label":"Antialiasing","run":"Section"}
%---
%[control:checkbox:0b3c]
%   data: {"defaultValue":true,"label":"Save full-size frames","run":"Section"}
%---
%[control:checkbox:0b3d]
%   data: {"defaultValue":true,"label":"Save POV-Ray scenes","run":"Section"}
%---
%[control:checkbox:0b3e]
%   data: {"defaultValue":true,"label":"Luminance column in the figure","run":"Section"}
%---
%[control:spinner:0b3f]
%   data: {"defaultValue":0,"label":"Dense continuum (0: default)","max":5000,"min":0,"run":"Section","runOn":"ValueChanged","step":1}
%---
%[control:slider:0b40]
%   data: {"defaultValue":0.5,"label":"Dense render resolution","max":1,"min":0.1,"run":"Section","runOn":"ValueChanged","step":0.05}
%---
%[control:spinner:0b41]
%   data: {"defaultValue":2,"label":"Dense render rays per pixel side","max":4,"min":1,"run":"Section","runOn":"ValueChanged","step":1}
%---
%[control:spinner:0b42]
%   data: {"defaultValue":0,"label":"Processes (0: automatic)","max":64,"min":0,"run":"Section","runOn":"ValueChanged","step":1}
%---
%[control:filebrowser:0b43]
%   data: {"browserType":"File","defaultValue":"\"\"","label":"Python interpreter","run":"Section"}
%---
%[control:checkbox:0b44]
%   data: {"defaultValue":false,"label":"Print progress","run":"Section"}
%---
