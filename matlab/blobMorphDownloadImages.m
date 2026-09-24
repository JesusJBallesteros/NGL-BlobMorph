function files = blobMorphDownloadImages(setName, destDir)
%BLOBMORPHDOWNLOADIMAGES Download an image set of the blob objects from coxlab/povray_blobs.
%
%   FILES = BLOBMORPHDOWNLOADIMAGES downloads the images of folder
%   images/Blobs_TrainingRatsD1D2 of https://github.com/coxlab/povray_blobs (objects 1 and 2
%   of Zoccolan et al. 2009, rotations -90 to 90 deg about the vertical axis) into
%   <BlobMorph>\Images\Blobs_TrainingRatsD1D2 and returns the full file names.
%
%   BLOBMORPHDOWNLOADIMAGES(SETNAME) downloads another folder of images/, for example
%   'Blobs_TrainingRatsD1D2_FinerSampling' or 'Blobs_Training_NewLighting_SoftShadow'.
%
%   BLOBMORPHDOWNLOADIMAGES(SETNAME, DESTDIR) saves the images in DESTDIR.
%
%   The images are not distributed with NGL BlobMorph. They belong to their authors
%   (Cox lab); publications using them cite Zoccolan et al. (2009).
%
%   See also BLOBMORPHMATRIX.

%   NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).

if nargin < 1 || isempty(setName)
    setName = 'Blobs_TrainingRatsD1D2';
end
root = fileparts(fileparts(mfilename('fullpath')));
if nargin < 2 || isempty(destDir)
    destDir = fullfile(root, 'Images', setName);
end
if ~isfolder(destDir)
    mkdir(destDir);
end

api = ['https://api.github.com/repos/coxlab/povray_blobs/contents/images/' setName];
list = webread(api, weboptions('Timeout', 60, 'ContentType', 'json'));
if isstruct(list)
    list = num2cell(list);
end

files = {};
for k = 1:numel(list)
    item = list{k};
    [~, ~, ext] = fileparts(item.name);
    if ~strcmp(item.type, 'file') || ~any(strcmpi(ext, {'.png', '.jpg', '.tif', '.bmp'}))
        continue
    end
    target = fullfile(destDir, item.name);
    websave(target, item.download_url, weboptions('Timeout', 60));
    files{end+1} = target; %#ok<AGROW>
end
fprintf('%d images saved in %s\n', numel(files), destDir);
end
