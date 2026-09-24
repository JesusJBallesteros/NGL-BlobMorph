function R = blobMorphLoad(outDir)
%BLOBMORPHLOAD Load the results of blobMorphMatrix (or of "python -m blobmorph").
%
%   R = blobMorphLoad(outDir) reads outDir/manifest.json and the images it lists.
%   Fields: levels, t, sizes, stimuli (sizes x levels cell of uint8), files, screens,
%   fullField (per size), luminance, lumPerSize, matrix, figureFile, manifest.
%
%   See also BLOBMORPHMATRIX.

%   NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).

mf = fullfile(outDir, 'manifest.json');
if ~isfile(mf)
    error('blobMorphLoad:manifest', 'No manifest.json in %s', outDir);
end
M = jsondecode(fileread(mf));
R = struct();
R.outputDir = outDir;
R.levels = M.levels_percent(:)';
R.t = M.t(:)';
R.sizes = M.sizes_deg(:)';
nS = numel(R.sizes);
nL = numel(R.levels);
files = localCell2D(M.stimulus_files, nS, nL);
screens = localCell2D(M.screen_files, nS, nL);
R.files = cell(nS, nL);
R.screens = cell(nS, nL);
R.stimuli = cell(nS, nL);
for i = 1:nS
    for j = 1:nL
        R.files{i, j} = fullfile(outDir, files{i, j});
        R.stimuli{i, j} = imread(R.files{i, j});
        if ~isempty(screens{i, j})
            R.screens{i, j} = fullfile(outDir, screens{i, j});
        end
    end
end
R.luminance = localNum2D(M.luminance_ff_level, nS, nL);
R.lumPerSize = M.luminance_ff_level_per_size(:)';
if isfield(M, 'fullfield_files')
    ff = M.fullfield_files;
    if ischar(ff), ff = {ff}; end
    R.fullField = cellfun(@(f) fullfile(outDir, f), ff(:)', 'UniformOutput', false);
end
R.figureFile = fullfile(outDir, M.figure);
R.matrix = imread(R.figureFile);
R.manifest = M;
end

function C = localCell2D(x, nS, nL)
% jsondecode returns nested string lists as cell/char arrays of varying shape
C = repmat({''}, nS, nL);
if isempty(x), return; end
if iscell(x) && numel(x) == nS && all(cellfun(@(r) iscell(r) || ischar(r), x))
    for i = 1:nS
        r = x{i};
        if ischar(r), r = {r}; end
        for j = 1:min(nL, numel(r))
            C{i, j} = r{j};
        end
    end
elseif iscell(x) && numel(x) == nS * nL
    C = reshape(x, nL, nS)';
end
end

function A = localNum2D(x, nS, nL)
if iscell(x)
    A = cell2mat(cellfun(@(r) r(:)', x, 'UniformOutput', false));
else
    A = x;
end
if ~isequal(size(A), [nS nL])
    A = reshape(A, nL, nS)';
end
end
