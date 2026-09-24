%% NGL BlobMorph master script
% Creates a morph matrix (morph levels x stimulus sizes) between two blob objects,
% following Rhee et al. (2025, Cell Reports, Fig. 1A and Fig. S4A) and Zoccolan et al.
% (2009, PNAS).
%
% Use:
%   0. Once: download the image bank with blobMorphDownloadImages (README, Image bank).
%   1. Set the parameters in sections 1 to 10 (section 1 is required, the others have
%      working defaults; the values given are examples from the project data).
%   2. Run the whole script (Editor tab > Run, or F5).
%   3. Results are written to OutputDir (section 0). The folder content is listed at the
%      end of the run and in section 12. The structure R stays in the workspace.
%
% Results (inside OutputDir):
%   figures\morph_matrix.png        morph matrix figure (also morph_matrix.pdf)
%   figures\morph_matrix_panel.png  morph matrix without labels
%   figures\distance_profile.png    pixel distance along the morph and chosen levels
%   stimuli\morphLL_levelPPP.PP_sizeSSS.S.png   one stimulus per morph level and size
%   screens\                        full-screen stimuli and full-field luminance controls
%   frames\                         full-size frame of each morph level
%   models\                         3-D model of each level (.json, .pov)
%   manifest.csv, manifest.json     list of stimuli, settings and results
%
% Help: README.md in the NGL-BlobMorph folder, "help blobMorphMatrix".
%
% NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).

%% 0. Folders (edit only if the folders are moved)
ToolboxDir = fileparts(fileparts(mfilename('fullpath')));  % NGL-BlobMorph folder
    if ~isfolder(fullfile(ToolboxDir, 'blobmorph'))             % section-by-section execution
        ToolboxDir = fileparts(fileparts(which('blobMorphMatrix')));
    end

% image bank of the project (download: blobMorphDownloadImages)
DataDir = fullfile(ToolboxDir, 'Images', 'Blobs_TrainingRatsD1D2');

% Folder for all results. Created if missing; files of a previous run are overwritten.
OutputDir = fullfile(ToolboxDir, 'results', 'morph_N1_N2');

%% 1. Required: input images
% ImageA: object at morph level 0 %
% ImageB: object at morph level 100 %
% Grayscale renders on a black background, both of the same size in pixels.
% Image bank (DataDir), 1078 x 617 px:
%   Blob_N1_CamRot_yRR.png  object 1 (object A), rotation RR about the vertical axis
%   Blob_N2_CamRot_yRR.png  object 2 (object B)
%   RR: -90 to 90 deg in steps of 15 deg; 0 = default view (Zoccolan et al. 2009, Fig. 1A)
% Rotated views morph at the same rotation, e.g. Blob_N1_CamRot_y30.png and
% Blob_N2_CamRot_y30.png.
%
% To morph object 2 into object 1, exchange ImageA and ImageB.
%
% With Method = 'models' (section 5) the images can be left empty ('').
ImageA = fullfile(DataDir, 'Blob_N1_CamRot_y0.png');
ImageB = fullfile(DataDir, 'Blob_N2_CamRot_y0.png');

%% 2. Morph matrix
% Number of morph levels, both original objects included.
% Examples: 9 (0, 12.5, ..., 100 %; Rhee et al. 2025, Fig. S4A), 22 (behavioural morph set).
NumLevels = 9;

% Stimulus sizes, degrees of visual angle.
% Examples: [10 20 30 40 50] (Rhee et al. 2025, Fig. S4A);
%           [15 20 25 30 35 40] (Zoccolan et al. 2009, Fig. 2).
Sizes = [10 20 30 40 50];

% Spacing of the morph levels:
%   'uniform'   equal steps of the morph parameter (levels of Fig. S4A)
%   'arc'       equal pixel-space Euclidean distance along the morph (Rhee et al. 2025, Methods)
%   'chord'     equal Euclidean distance between successive chosen levels
%   'original'  procedure of julianarhee/morph-pov: 2000 morphs, nearest level (about 25 min)
Sampling = 'uniform';

%% 3. Display: degrees to pixels
% Option A: pixels per degree of visual angle. Used when not empty.
% Example: 16.05 (two-photon imaging display, Rhee et al. 2025).
PixelsPerDegree = 16.05;

% Option B: screen geometry. Used when PixelsPerDegree is empty.
% Example (Zoccolan et al. 2009): Samsung SyncMaster 940BX, 1280 x 1024 px, 37.6 cm wide,
% eyes at 25 cm: ScreenPixels = [1280 1024]; ScreenWidthCm = 37.6; ViewingDistanceCm = 25;
ScreenPixels      = [1920 1080];  % [width height] in pixels, also the size of the screen images
ScreenWidthCm     = [];           % visible width of the screen (cm)
ViewingDistanceCm = [];           % eye to screen distance (cm)

% Conversion for option B:
%   'mworks'   linear in degrees over the whole screen (MWorks convention)
%   'tangent'  exact visual angle of a stimulus centred on the line of sight
%   'linear'   small-angle approximation
DegreeMode = 'mworks';

% Centre of the stimulus on the screen images, [x y] degrees from the screen centre
% (x to the right, y upwards).
StimulusPositionDeg = [0 0];

% Dimension of the stimulus that spans the size in degrees:
%   'crop_max'     longest side of the common crop of all levels (one scale for all levels)
%   'crop_width', 'crop_height'
%   'object_max'   longest side of each object's own bounding box
SizeReference = 'crop_max';

%% 4. Luminance controls and figure
% Display gamma used for the luminance-matched full-field grey levels (1 = linearised display).
DisplayGamma = 2.2;

% Save a full-screen image of each stimulus (screens folder).
SaveScreens = true;

% Luminance column of the figure:
%   'actual'     computed full-field grey level of each size
%   'schematic'  255 x size / largest size (as drawn in Fig. S4A)
LuminanceDisplay = 'schematic';

% Figure title ('' for none).
FigureTitle = '';

%% 5. Object models
% Source of the 3-D model of each object:
%   'auto'    recognise the two reference objects (Zoccolan et al. 2009), otherwise fit
%   'preset'  reference objects only (error if the images are not recognised)
%   'fit'     fit blob models to the images (about 11 min per image)
%   'models'  use ModelA and ModelB
Method = 'auto';

% Blob models, POV-Ray scene (.pov) or model file (.json). '' when not used.
% Examples:
%   POV-Ray scene files of the reference objects:
%     ModelA = fullfile(ToolboxDir, 'tests', 'povray_reference', 'obj1_cam11_v36.pov');
%     ModelB = fullfile(ToolboxDir, 'tests', 'povray_reference', 'obj2_cam11_v36.pov');
%   Models fitted in a previous run (no refitting):
%     ModelA = fullfile(ToolboxDir, 'examples', 'fitted_from_images', 'models', 'fitted_A.json');
%     ModelB = fullfile(ToolboxDir, 'examples', 'fitted_from_images', 'models', 'fitted_B.json');
ModelA = '';
ModelB = '';

% Values of identifiers left free in .pov files (POV-Ray option Declare=name=value).
% Example for coxlab/povray_blobs StimBlob_lighting_new_call_2.pov:
%   PovDeclare = struct('obj_pos_x', 0, 'obj_pos_y', 0, 'obj_pos_z', 6, ...
%       'obj_scale_x', 0, 'obj_scale_y', 0, 'obj_scale_z', 0, ...
%       'cam_rot_x', 0, 'cam_rot_y', 0, 'cam_rot_z', 0, ...
%       'light_pos_x', 0, 'light_pos_y', -10, 'light_pos_z', -10);
PovDeclare = struct();

% Rendering set-up for fitted objects and model files (reference objects: calibrated
% automatically):
%   'auto'          fitted objects: camera z = -11, tone curve 'zoccolan', antialiasing as
%                   the input images; fitted models (.json): set-up stored in the file;
%                   .pov files: camera of the scene file, tone curve calibrated on the
%                   images (linear without images)
%   'provided'      camera z = -11, tone curve 'zoccolan'
%   'zoccolan2009'  camera z = -10, linear output
%   'rhee2025'      camera z = -10, sRGB output, no antialiasing
%   struct: struct('preset', 'provided', 'cam_location', [0 0 -11], ...
%                  'light', [0 -10 -10], 'tone', 'zoccolan')
%           tone: 'zoccolan', 'linear', 'srgb', 'gamma:2.2' or a 256-value LUT file
Setup = 'auto';

%% 6. Correspondence between object parts (objects other than the reference pair)
% 'match'      matched parts are interpolated, the other parts fade in or out
% 'crossfade'  all parts of A fade out while all parts of B fade in
% 'index'      part i of A becomes part i of B (same number of parts)
Correspondence = 'match';

% Parts without a partner: 'fade' (strength to 0) or 'shrink' (radius to 0).
Vanish = 'fade';

% Interpolation of matched parts:
%   'auto'       'geometric' for fitted models, 'pov' otherwise
%   'pov'        linear on the POV-Ray numbers (translate, scale, rotate, radius, strength)
%   'geometric'  centre, semi-axes and orientation of each ellipsoid
Interpolation = 'auto';

%% 7. Image fitting (Method 'fit', or 'auto' with objects not recognised)
FitSymmetric     = 'auto';  % left-right symmetric model: 'auto', true or false
FitMaxComponents = 4;       % maximum number of lobes taken from the silhouette
FitMaxExtra      = 2;       % maximum number of parts added inside the silhouette
FitRestarts      = 1;       % independent runs of the first stage
FitPopulation    = 16;      % CMA-ES population size
FitSeed          = 0;       % random seed
% One row per stage: [resolution factor, supersampling, maximum generations, initial step].
FitStages = [0.15 2 160 1.0
             0.30 2  70 0.3
             0.50 1  40 0.1];

%% 8. Post-processing of the rendered frames
UseInputsAsAnchors = false;      % true: levels 0 % and 100 % are the input images
Center             = 'anchors';  % 'anchors': centre the joint bounding box of both objects; 'none'
CenterHorizontal   = true;       % also centre horizontally
CropMargin         = 2;          % margin in pixels around the joint bounding box of all levels
Antialias          = 'auto';     % antialiasing of the final renders: 'auto' (as the input images), true or false
SaveFrames         = true;       % full-size frames (frames folder)
SavePov            = true;       % POV-Ray scene of each level (models folder)
LuminanceColumn    = true;       % luminance column in the figure

%% 9. Performance
NumDense         = [];   % morphs of the dense continuum ([]: 201; 2002 for 'original')
DenseScale       = 0.5;  % resolution factor of the dense continuum renders
DenseSupersample = 2;    % rays per pixel side in the dense continuum renders
Processes        = [];   % parallel Python processes ([]: min(8, number of cores / 2))

%% 10. Environment
% Python interpreter with numpy, scipy, pillow and matplotlib.
% '': first working one among pyenv, python, python3 and py -3.
% Example: 'C:\Users\<user>\AppData\Local\Programs\Python\Python313\python.exe'
PythonExe  = '';
Verbose    = true;   % print progress
ShowFigure = true;   % open the morph matrix figure at the end

%% 11. Run (no changes needed below)
addpath(fullfile(ToolboxDir, 'matlab'));
if ~strcmpi(Method, 'models')
    assert(isfile(ImageA), ['ImageA not found: %s\nImage bank: run ' ...
        'blobMorphDownloadImages (README, Image bank).'], ImageA);
    assert(isfile(ImageB), 'ImageB not found: %s', ImageB);
end

args = {'NumLevels', NumLevels, 'Sizes', Sizes, 'Sampling', Sampling, ...
    'ScreenPixels', ScreenPixels, 'DegreeMode', DegreeMode, ...
    'StimulusPositionDeg', StimulusPositionDeg, 'SizeReference', SizeReference, ...
    'DisplayGamma', DisplayGamma, 'SaveScreens', SaveScreens, ...
    'LuminanceDisplay', LuminanceDisplay, 'Title', FigureTitle, 'Method', Method, ...
    'Setup', Setup, 'Correspondence', Correspondence, 'Vanish', Vanish, ...
    'OutputDir', OutputDir, 'Python', PythonExe, 'Verbose', Verbose, 'ShowFigure', ShowFigure};
if ~isempty(PixelsPerDegree),   args = [args, {'PixelsPerDegree', PixelsPerDegree}]; end
if ~isempty(ScreenWidthCm),     args = [args, {'ScreenWidthCm', ScreenWidthCm}]; end
if ~isempty(ViewingDistanceCm), args = [args, {'ViewingDistanceCm', ViewingDistanceCm}]; end
if ~isempty(ModelA),            args = [args, {'ModelA', ModelA, 'ModelB', ModelB}]; end
if ~isempty(NumDense),          args = [args, {'NumDense', NumDense}]; end
if ~isempty(Processes),         args = [args, {'Processes', Processes}]; end

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

R = blobMorphMatrix(ImageA, ImageB, args{:});

%% 12. Results
% R.levels      morph levels (%)            R.t        morph parameter (0 = A, 1 = B)
% R.sizes       sizes (deg)                 R.stimuli  {size, level} uint8 images
% R.files       {size, level} file names    R.screens  {size, level} screen image files
% R.luminance   {size, level} full-field grey levels; R.lumPerSize: mean per size
% R.matrix      morph matrix figure (RGB);  R.figureFile, R.manifest
% Example: R.stimuli{R.sizes == 30, R.levels == 50} is the 50 % morph at 30 deg.
StimulusTable = blobMorphReport(R);
