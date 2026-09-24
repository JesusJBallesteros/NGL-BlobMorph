function T = blobMorphReport(R)
%BLOBMORPHREPORT List the output files of blobMorphMatrix.
%
%   T = blobMorphReport(R) prints the results folder and its content, and returns a table
%   with one row per stimulus (morph level, morph parameter t, size, file names, size in
%   pixels, luminance-matched full-field grey level).
%
%   See also BLOBMORPHMATRIX, BLOBMORPHLOAD.

%   NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).

out = R.outputDir;
s = filesep;
items = {
    ['figures' s 'morph_matrix.png'], 'morph matrix figure (also morph_matrix.pdf)'
    ['figures' s 'morph_matrix_panel.png'], 'morph matrix without labels'
    ['figures' s 'distance_profile.png'], 'pixel distance along the morph, chosen levels'
    ['stimuli' s], sprintf('%d stimuli, morphLL_levelPPP.PP_sizeSSS.S.png', numel(R.files))
    ['screens' s], 'full-screen stimuli, fullfield_luminance_sizeSSS.S.png controls'
    ['frames' s], 'full-size frame of each morph level'
    ['models' s], '3-D model of each level (.json, .pov)'
    'manifest.csv', 'one row per stimulus (returned as a table)'
    'manifest.json', 'all settings and results'
    };
fprintf('\nResults folder:\n  %s\n\n', out);
for k = 1:size(items, 1)
    fprintf('  %-32s %s\n', items{k, 1}, items{k, 2});
end
fprintf('\nMorph levels (%%):  %s\n', mat2str(R.levels, 4));
fprintf('Sizes (deg):       %s\n', mat2str(R.sizes, 4));
fprintf('Full-field grey level per size: %s\n\n', mat2str(R.lumPerSize, 4));
T = readtable(fullfile(out, 'manifest.csv'), 'Delimiter', ',', 'TextType', 'string');
end
