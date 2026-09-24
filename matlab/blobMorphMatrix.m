function R = blobMorphMatrix(imageA, imageB, varargin)
%BLOBMORPHMATRIX Morph matrix (morph levels x sizes) between two "blob" object images.
%
%   R = blobMorphMatrix(imageA, imageB) creates the morph continuum between the objects of
%   the two images (object A: morph level 0 %, object B: 100 %), selects NumLevels morphs
%   and renders each morph at each size, as in Rhee et al. (2025, Cell Reports, Fig. 1A and
%   Fig. S4A). The objects are those of Zoccolan et al. (2009, PNAS).
%
%   The morph interpolates the parameters (translate, scale, rotate, radius, strength) of
%   the 3-D POV-Ray blob models of the two objects, as in
%   julianarhee/morph-pov/make_pov_morphs.py. Models:
%     * objects 1 and 2 of Zoccolan et al. (2009): recognised in the images; scene files of
%       coxlab/povray_blobs; camera, centring shift and tone curve calibrated on the images;
%     * other blob images: models fitted to the images ('Method');
%     * POV-Ray (.pov) or JSON models given with 'ModelA' and 'ModelB'.
%
%   Script with all parameters and examples: blobMorph_master.m (live script:
%   blobMorph_live.m).
%
%   R = blobMorphMatrix(imageA, imageB, Name, Value, ...) options:
%     'NumLevels'         9                 morph levels, including both originals
%     'Sizes'             [10 20 30 40 50]  stimulus sizes, degrees of visual angle
%     'OutputDir'         './morph_matrix_output'
%     'Sampling'          'arc'   'arc'      equal Euclidean pixel distance along the morph
%                                 'original' procedure of julianarhee/morph-pov: 2000
%                                            full-size morphs, utils/euclid.py
%                                 'chord'    equal distance between successive chosen morphs
%                                 'uniform'  equal steps of the morph parameter (Fig. S4A)
%     'Method'            'auto'  'auto' | 'preset' | 'fit' | 'models'
%     'ModelA','ModelB'   ''      blob models (.pov as in coxlab/povray_blobs, or .json)
%     'Setup'             'auto'  'auto' | 'provided' | 'zoccolan2009' | 'rhee2025'
%     'PixelsPerDegree'   []      default 16.05 (Rhee et al. imaging display)
%     'ScreenPixels'      [1920 1080]
%     'ScreenWidthCm'     []      \ used instead of PixelsPerDegree when both given
%     'ViewingDistanceCm' []      /
%     'DegreeMode'        'mworks' 'mworks' | 'tangent' | 'linear'
%     'SizeReference'     'crop_max'  what spans Size degrees: longest side of the common
%                                 crop ('crop_max'), its width/height, or 'object_max'
%     'StimulusPositionDeg' [0 0]
%     'DisplayGamma'      2.2     for the luminance-matched full-field levels
%     'SaveScreens'       true    also save full-screen images
%     'LuminanceDisplay'  'actual' matrix figure column: 'actual' | 'schematic' (Fig. S4A)
%     'Correspondence'    'match' part matching for objects other than objects 1 and 2
%                                 ('match' | 'crossfade' | 'index')
%     'Vanish'            'fade'  unmatched components: 'fade' (strength) | 'shrink' (radius)
%     'NumDense'          []      dense continuum size (default 201; 2002 for 'original')
%     'Processes'         []      parallel worker processes (default min(8, cores/2))
%     'Title'             ''
%     'Python'            ''      python executable (default: the first of pyenv's
%                                 interpreter, 'python', 'python3', 'py -3' that has
%                                 numpy, scipy, pillow and matplotlib)
%     'Verbose'           true
%     'ShowFigure'        true
%     'Advanced'          struct() further options of the Python back end (blobMorph_master.m,
%                                 sections 6 to 9), e.g.
%                                 struct('use_inputs_as_anchors', true, 'interpolation',
%                                 'geometric', 'pov_declare', struct('obj_pos_z', 6))
%
%   Output struct R:
%     levels     1 x L morph levels (%)          t        1 x L morph parameter
%     sizes      1 x S sizes (deg)               stimuli  S x L cell of uint8 images
%     files      S x L cell of stimulus files    screens  S x L cell of screen files
%     luminance  S x L luminance-matched full-field grey levels (per size: lumPerSize)
%     matrix     RGB image of the morph-matrix figure, figureFile, manifest (all details)
%
%   Example (image bank, README):
%     R = blobMorphMatrix('Blob_N1_CamRot_y0.png', 'Blob_N2_CamRot_y0.png', ...
%                         'NumLevels', 9, 'Sizes', 10:10:50, 'Sampling', 'uniform', ...
%                         'OutputDir', 'morphs');
%
%   Requires Python 3 with numpy, scipy, pillow and matplotlib.
%   See also BLOBMORPHLOAD, BLOBMORPHREPORT, BLOBMORPHPYTHON, BLOBMORPHDOWNLOADIMAGES.

%   NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).

p = inputParser;
p.FunctionName = 'blobMorphMatrix';
addOptional(p, 'imageA', '', @(x) ischar(x) || isstring(x));
addOptional(p, 'imageB', '', @(x) ischar(x) || isstring(x));
addParameter(p, 'NumLevels', 9, @(x) isnumeric(x) && isscalar(x) && x >= 2);
addParameter(p, 'Sizes', [10 20 30 40 50], @(x) isnumeric(x) && all(x > 0));
addParameter(p, 'OutputDir', fullfile(pwd, 'morph_matrix_output'), @(x) ischar(x) || isstring(x));
addParameter(p, 'Sampling', 'arc', @(x) any(strcmpi(x, {'arc', 'chord', 'original', 'uniform'})));
addParameter(p, 'Method', 'auto', @(x) any(strcmpi(x, {'auto', 'preset', 'fit', 'models'})));
addParameter(p, 'ModelA', '', @(x) ischar(x) || isstring(x));
addParameter(p, 'ModelB', '', @(x) ischar(x) || isstring(x));
addParameter(p, 'Setup', 'auto', @(x) ischar(x) || isstring(x) || isstruct(x));
addParameter(p, 'PixelsPerDegree', [], @(x) isempty(x) || (isnumeric(x) && isscalar(x)));
addParameter(p, 'ScreenPixels', [1920 1080], @(x) isnumeric(x) && numel(x) == 2);
addParameter(p, 'ScreenWidthCm', [], @(x) isempty(x) || isscalar(x));
addParameter(p, 'ViewingDistanceCm', [], @(x) isempty(x) || isscalar(x));
addParameter(p, 'DegreeMode', 'mworks', @(x) any(strcmpi(x, {'mworks', 'tangent', 'linear'})));
addParameter(p, 'SizeReference', 'crop_max', @(x) ischar(x) || isstring(x));
addParameter(p, 'StimulusPositionDeg', [0 0], @(x) isnumeric(x) && numel(x) == 2);
addParameter(p, 'DisplayGamma', 2.2, @(x) isnumeric(x) && isscalar(x));
addParameter(p, 'SaveScreens', true, @(x) islogical(x) || isnumeric(x));
addParameter(p, 'LuminanceDisplay', 'actual', @(x) any(strcmpi(x, {'actual', 'schematic'})));
addParameter(p, 'Correspondence', 'match', @(x) any(strcmpi(x, {'match', 'crossfade', 'index'})));
addParameter(p, 'Vanish', 'fade', @(x) any(strcmpi(x, {'fade', 'shrink'})));
addParameter(p, 'NumDense', [], @(x) isempty(x) || isscalar(x));
addParameter(p, 'Processes', [], @(x) isempty(x) || isscalar(x));
addParameter(p, 'Title', '', @(x) ischar(x) || isstring(x));
addParameter(p, 'Python', '', @(x) ischar(x) || isstring(x));
addParameter(p, 'Verbose', true, @(x) islogical(x) || isnumeric(x));
addParameter(p, 'ShowFigure', true, @(x) islogical(x) || isnumeric(x));
addParameter(p, 'Advanced', struct(), @isstruct);
if nargin < 1, imageA = ''; end
if nargin < 2, imageB = ''; end
parse(p, imageA, imageB, varargin{:});
o = p.Results;

% ---------------------------------------------------------------------------- config ----
outDir = char(o.OutputDir);
if ~isfolder(outDir), mkdir(outDir); end
outDir = localAbs(outDir);
cfg = struct();
if ~isempty(char(o.imageA)), cfg.image_a = localAbs(char(o.imageA)); end
if ~isempty(char(o.imageB)), cfg.image_b = localAbs(char(o.imageB)); end
if ~isempty(char(o.ModelA)), cfg.model_a = localAbs(char(o.ModelA)); end
if ~isempty(char(o.ModelB)), cfg.model_b = localAbs(char(o.ModelB)); end
if ~(isfield(cfg, 'image_a') && isfield(cfg, 'image_b')) && ...
        ~(isfield(cfg, 'model_a') && isfield(cfg, 'model_b'))
    error('blobMorphMatrix:input', 'Give two images (or ModelA and ModelB).');
end
cfg.method = lower(char(o.Method));
cfg.setup = o.Setup;
if isstring(cfg.setup), cfg.setup = char(cfg.setup); end
cfg.n_levels = o.NumLevels;
cfg.sizes = num2cell(double(o.Sizes(:)'));      % always a JSON array
cfg.sampling = lower(char(o.Sampling));
cfg.correspondence = lower(char(o.Correspondence));
cfg.vanish = lower(char(o.Vanish));
cfg.size_reference = char(o.SizeReference);
if ~isempty(o.PixelsPerDegree), cfg.px_per_deg = o.PixelsPerDegree; end
cfg.screen_px = num2cell(double(o.ScreenPixels(:)'));
if ~isempty(o.ScreenWidthCm), cfg.screen_cm = o.ScreenWidthCm; end
if ~isempty(o.ViewingDistanceCm), cfg.distance_cm = o.ViewingDistanceCm; end
cfg.deg_mode = lower(char(o.DegreeMode));
cfg.stim_pos_deg = num2cell(double(o.StimulusPositionDeg(:)'));
cfg.display_gamma = o.DisplayGamma;
cfg.save_screens = logical(o.SaveScreens);
cfg.luminance_display = lower(char(o.LuminanceDisplay));
if ~isempty(o.NumDense), cfg.n_dense = o.NumDense; end
if ~isempty(o.Processes), cfg.processes = o.Processes; end
if ~isempty(char(o.Title)), cfg.title = char(o.Title); end
cfg.verbose = logical(o.Verbose);
cfg.out_dir = outDir;
adv = fieldnames(o.Advanced);
for k = 1:numel(adv)
    cfg.(adv{k}) = o.Advanced.(adv{k});
end
cfgFile = fullfile(outDir, 'blobmorph_config.json');
fid = fopen(cfgFile, 'w');
fwrite(fid, jsonencode(cfg, 'PrettyPrint', true), 'char');
fclose(fid);

% ---------------------------------------------------------------------------- python ----
toolboxRoot = fileparts(fileparts(mfilename('fullpath')));   % folder containing 'blobmorph'
oldPP = getenv('PYTHONPATH');
cleanup = onCleanup(@() setenv('PYTHONPATH', oldPP));
setenv('PYTHONPATH', strjoin([{toolboxRoot}, {oldPP}], pathsep));
py = blobMorphPython(char(o.Python));
cmd = sprintf('%s -m blobmorph --config "%s"', py, cfgFile);
if o.Verbose
    fprintf('Running: %s\n', cmd);
    status = system(cmd, '-echo');
else
    [status, txt] = system(cmd);
    if status ~= 0, fprintf('%s\n', txt); end
end
if status ~= 0
    error('blobMorphMatrix:python', 'The Python back end failed (status %d), see the messages above.', ...
        status);
end

% ---------------------------------------------------------------------------- results ---
R = blobMorphLoad(outDir);
if o.ShowFigure
    figure('Name', 'Morph matrix', 'Color', 'w');
    imshow(R.matrix, 'Border', 'tight');
end
end

function p = localAbs(p)
% absolute path
if isempty(p), return; end
isAbs = startsWith(p, {'/', '\'}) || ~isempty(regexp(p, '^[A-Za-z]:[\\/]', 'once'));
if ~isAbs
    p = fullfile(pwd, p);
end
end
