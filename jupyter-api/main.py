import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import re

def stats(filepath):
    with open(filepath) as f:
        nb = nbformat.read(f, as_version=4)

    print("There are %d cells" % len(nb.cells))

    error_outputs = [x for c in nb.cells for x in c.outputs if x.output_type == 'error']

    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    print("There are %d errors" % len(error_outputs))
    for output in error_outputs:
        print("\n".join(ansi_escape.sub('', x) for x in output.traceback))

    return nb

def run(in_path, out_path):
    with open(in_path) as f:
        nb = nbformat.read(f, as_version=4)

    proc = ExecutePreprocessor(timeout=10, kernel_name='python3')
    proc.allow_errors = True
    proc.preprocess(nb, {'metadata': {'path': '.'}})

    with open(out_path, 'wt') as f:
        nbformat.write(nb, f)

if __name__ == '__main__':
    stats('a.ipynb')
    run('a.ipynb', 'b.ipynb')
    stats('b.ipynb')
