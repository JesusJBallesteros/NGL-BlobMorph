function [py, info] = blobMorphPython(pythonExe)
%BLOBMORPHPYTHON Python interpreter used by blobMorphMatrix.
%
%   PY = BLOBMORPHPYTHON returns the command of the first interpreter among the
%   interpreter of pyenv, python, python3 and py -3 that imports numpy, scipy, pillow and
%   matplotlib. The result is kept for the MATLAB session.
%
%   PY = BLOBMORPHPYTHON(PYTHONEXE) checks the interpreter PYTHONEXE.
%
%   [PY, INFO] = BLOBMORPHPYTHON(...) also returns the versions of Python and of the
%   packages as text.
%
%   See also BLOBMORPHMATRIX.

%   NGL BlobMorph. Copyright (c) 2026 Jesus J. Ballesteros. MIT Licence (see LICENSE).

persistent cache
if nargin < 1
    pythonExe = '';
end
pythonExe = char(pythonExe);
if isempty(pythonExe) && ~isempty(cache)
    py = cache;
else
    cands = {};
    if ~isempty(pythonExe)
        cands{end+1} = ['"' pythonExe '"'];
    else
        try
            pe = pyenv;
            if strlength(pe.Executable) > 0 && isfile(pe.Executable)
                cands{end+1} = ['"' char(pe.Executable) '"'];
            end
        catch
        end
        cands = [cands, {'python', 'python3'}];
        if ispc
            cands{end+1} = 'py -3';
        end
    end
    py = '';
    for k = 1:numel(cands)
        [st, ~] = system([cands{k} ' -c "import numpy, scipy, PIL, matplotlib"']);
        if st == 0
            py = cands{k};
            break
        end
    end
    if isempty(py)
        error('blobMorphPython:notFound', ['No Python interpreter with numpy, scipy, ' ...
            'pillow and matplotlib was found (tried: %s). Install them with ' ...
            '"python -m pip install numpy scipy pillow matplotlib" or give the ' ...
            'interpreter (PythonExe).'], strjoin(cands, ', '));
    end
    if isempty(pythonExe)
        cache = py;
    end
end
if nargout > 1
    [~, info] = system([py ' -c "import sys, numpy, scipy, PIL, matplotlib; ' ...
        'print(''Python'', sys.version.split()[0], ''| numpy'', numpy.__version__, ' ...
        '''| scipy'', scipy.__version__, ''| pillow'', PIL.__version__, ' ...
        '''| matplotlib'', matplotlib.__version__)"']);
    info = strtrim(info);
end
end
