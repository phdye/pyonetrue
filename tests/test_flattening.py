import pytest
from pathlib import Path

import textwrap

from pyonetrue import FlatteningContext, FlatteningModule

def test_flatten_context_preserves_order(tmp_path):
    mod1 = tmp_path / 'mod1.py'
    mod1.write_text(textwrap.dedent("""
        import os
        def a(): pass
        if __name__ == '__main__':
            a()
    """))
    mod2 = tmp_path / 'mod2.py'
    mod2.write_text(textwrap.dedent("""
        from sys import argv
        def b(): pass
        if __name__ == '__main__':
            b()
    """))
    ctx = FlatteningContext(package_path=tmp_path)
    ctx.add_module(mod1)
    ctx.add_module(str(mod2))
    spans = ctx.get_final_output_spans()
    # print("\n") ; [ print(span) for span in spans ] ; print("\n")
    assert spans[0].text.startswith('import os')
    assert spans[1].text.startswith('from sys import argv')
    # functions
    assert any(s.kind == 'function' for s in spans)
    # main guards
    assert all(s.kind == 'main_guard' for s in spans if s.kind == 'main_guard')

def test_flatten_clashes(tmp_path):
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_text("def dup(): pass")
    f2.write_text("def dup(): pass")
    ctx = FlatteningContext(package_path=tmp_path)
    ctx.add_module(f1)
    ctx.add_module(f2)
    with pytest.raises(Exception):
        ctx.get_final_output_spans()

def test_flatten_multiple_guards(tmp_path):
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_text("if __name__=='__main__': a=1")
    f2.write_text("if __name__=='__main__': b=2")
    ctx = FlatteningContext(package_path=tmp_path)
    ctx.add_module(f1)
    ctx.add_module(f2)
    spans = ctx.get_final_output_spans(include_all_guards=True)
    texts = [s.text for s in spans if s.kind=='main_guard']
    assert "a=1" in "".join(texts) and "b=2" in "".join(texts)

def test_flatten_omit_guards_default(tmp_path):
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_text("if __name__=='__main__': a=1")
    f2.write_text("if __name__=='__main__': b=2")
    ctx = FlatteningContext(package_path=tmp_path)
    ctx.add_module(f1)
    ctx.add_module(f2)
    spans = ctx.get_final_output_spans()
    texts = [s.text for s in spans if s.kind=='main_guard']
    assert "a=1" not in "".join(texts) and "b=2" not in "".join(texts)

def test_flattening_context_init_with_directory(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    ctx = FlatteningContext(str(pkg))
    assert ctx.package_path == pkg
    assert ctx.package_name == "mypkg"

def test_flattening_context_init_with_file(tmp_path):
    file = tmp_path / "module.py"
    file.write_text("""
    import os
    """)
    ctx = FlatteningContext(str(file))
    assert ctx.package_path == file
    assert ctx.package_name == "module"

def test_flattening_context_invalid_package_path():
    with pytest.raises(ValueError):
        FlatteningContext("/nonexistent/path")

def test_new_module_correct_mapping(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "mod.py").write_text("")
    ctx = FlatteningContext(str(pkg))
    fm = ctx.new_module(pkg / "mod.py")
    assert fm.module == "mypkg.mod"

def test_new_module_outside_package_root(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    other_file = tmp_path / "outside.py"
    other_file.write_text("")
    ctx = FlatteningContext(str(pkg))
    with pytest.raises(ValueError):
        ctx.new_module(other_file)

def test_add_module_from_path(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("import os")
    ctx = FlatteningContext(str(pkg))
    ctx.add_module(pkg / "__init__.py")
    assert any("import" in span.kind for mod, spans in ctx.module_spans for span in spans)

def test_add_module_records_main_guard(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "runner.py").write_text("if __name__ == '__main__':\n    print('Hello')")
    ctx = FlatteningContext(str(pkg))
    ctx.add_module(pkg / "runner.py")
    assert any("runner" in k for k in ctx.guard_sources)

def test_output_spans_order_correct(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("import os\ndef foo(): pass\n")
    ctx = FlatteningContext(str(pkg))
    ctx.add_module(pkg / "mod.py")
    spans = ctx.get_final_output_spans()
    kinds = [s.kind for s in spans]    
    assert kinds.index("import") < kinds.index("function")

def test_output_spans_includes_guards_if_requested(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "run.py").write_text("if __name__ == '__main__':\n    pass\n")
    ctx = FlatteningContext(str(pkg))
    ctx.add_module(pkg / "run.py")
    spans = ctx.get_final_output_spans(include_all_guards=True)
    assert any(s.kind == "main_guard" for s in spans)

def test_output_spans_omits_guards_by_default(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "run.py").write_text("if __name__ == '__main__':\n    pass\n")
    ctx = FlatteningContext(str(pkg))
    ctx.add_module(pkg / "run.py")
    spans = ctx.get_final_output_spans()
    assert all(s.kind != "main_guard" for s in spans)

def test_clash_detection_duplicate_function_names(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("def foo(): pass")
    (pkg / "b.py").write_text("def foo(): pass")
    ctx = FlatteningContext(str(pkg))
    ctx.add_module(pkg / "a.py")
    ctx.add_module(pkg / "b.py")
    with pytest.raises(Exception, match="Duplicate top-level name detected"):
        ctx.get_final_output_spans()

def test_ignore_clashes_flag(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("def foo(): pass")
    (pkg / "b.py").write_text("def foo(): pass")
    ctx = FlatteningContext(str(pkg))
    ctx.add_module(pkg / "a.py")
    ctx.add_module(pkg / "b.py")
    spans = ctx.get_final_output_spans(ignore_clashes=True)
    assert any("foo" in s.text for s in spans)

def test_flatteningmodule_correct_module_dotted_name(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "sub.py").write_text("")
    ctx = FlatteningContext(str(pkg))
    fm = FlatteningModule(ctx, pkg / "sub.py")
    assert fm.module == "mypkg.sub"

def test_flatteningmodule_error_if_not_under_root(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    other_file = tmp_path / "outsider.py"
    other_file.write_text("")
    ctx = FlatteningContext(str(pkg))
    with pytest.raises(ValueError):
        FlatteningModule(ctx, other_file)

def test_flatteningmodule_init_with_init_py(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    init = (pkg / "__init__.py")
    init.write_text("")
    ctx = FlatteningContext(pkg)
    fm = FlatteningModule(ctx, init)
    assert fm.module == "mypkg"

def test_every_span_followed_by_blank(tmp_path):
    pkg = tmp_path / "demo2"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        "from math import sqrt\n\ndef bar():\n    pass\nclass X: pass\n"
    )

    ctx = FlatteningContext(package_path=pkg)
    ctx.discover_modules()
    spans = ctx.get_final_output_spans()

    real_kinds = {"class", "function", "logic", "main_guard", "meta"}
    for i in range(len(spans) - 1):
        if spans[i].kind in real_kinds:
            assert spans[i + 1].kind == "blank", f"Span at index {i} not followed by blank line"


def test_all_inserted_after_imports(tmp_path):
    pkg = tmp_path / "demo"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        "from os import path\nfrom sys import version\n\ndef foo():\n    pass\n\n__all__ = ['foo']\n\n"
    )

    ctx = FlatteningContext(package_path=pkg)
    ctx.discover_modules()
    spans = ctx.get_final_output_spans()

    found_all = False
    for i, span in enumerate(spans):
        if "__all__" in span.text:
            found_all = True
            assert spans[i - 1].kind == "blank", "__all__ must be preceded by one blank line"
            for j in range(i - 1, -1, -1):
                if spans[j].kind != "blank":
                    assert spans[j].kind == "import", "__all__ must follow import group"
                    break
            break
    assert found_all, "__all__ not found in flattened output"

def test_flattening_preserves_adjacent_dataclass(tmp_path):

    # Create a simple source file with @dataclass and class MyOptions
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "opts.py").write_text('''
from dataclasses import dataclass

@dataclass
class MyOptions:
    x: int
    y: str
''')

    # Build flattening context and extract flattened spans
    ctx = FlatteningContext(package_path=pkg)
    ctx.discover_modules()
    spans = ctx.get_final_output_spans()

    # Flatten into a text buffer
    flat = "\n".join(span.text for span in spans)

    # Check for adjacent @dataclass + class MyOptions
    lines = flat.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "@dataclass":
            for j in range(i + 1, len(lines)):
                if lines[j].strip():  # first non-blank line
                    assert lines[j].strip().startswith("class MyOptions"), (
                        f"Expected 'class MyOptions' after @dataclass, got: {lines[j]}"
                    )
                    return
    assert False, "No adjacent @dataclass followed by class MyOptions found"
