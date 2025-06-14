import textwrap
from pyonetrue.vendor.pathlib import Path
from pyonetrue import FlatteningContext


def test_future_import_after_docstring(tmp_path):
    pkg = tmp_path / 'pkg'
    pkg.mkdir()
    source = textwrap.dedent('''
        """module docstring"""
        from __future__ import print_function
        import os
        def foo():
            pass
    ''')
    (pkg / '__init__.py').write_text(source)

    ctx = FlatteningContext(package_path=pkg)
    ctx.add_module(pkg / '__init__.py')
    spans = ctx.get_final_output_spans()
    text = ''.join(span.text for span in spans)
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    assert lines[0] == '"""module docstring"""'
    assert lines[1] == 'from __future__ import print_function'
    assert lines[2] == 'import os'
