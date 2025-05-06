import pytest
from pathlib import Path

import textwrap

from pyonetrue import (
    FlatteningContext,
    FlatteningModule,
    normalize_a_module_name,
    normalize_module_names,
    CLIOptionError,
    DuplicateNameError,
    IncludeExcludeError,
    FlatteningError,
    ModuleInferenceError,
    PathError,
)

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
    with pytest.raises(DuplicateNameError):
        ctx.get_final_output_spans()

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
    with pytest.raises(ModuleInferenceError):
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
    with pytest.raises(PathError, match=r"Path .* is not inside package root .*"):
        ctx.new_module(other_file)

def test_add_module_from_path(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("import os")
    ctx = FlatteningContext(str(pkg))
    ctx.add_module(pkg / "__init__.py")
    assert any("import" in span.kind for mod, spans in ctx.module_spans for span in spans)

def test_output_spans_order_correct(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("import os\ndef foo(): pass\n")
    ctx = FlatteningContext(str(pkg))
    ctx.add_module(pkg / "mod.py")
    spans = ctx.get_final_output_spans()
    kinds = [s.kind for s in spans]    
    assert kinds.index("import") < kinds.index("function")

def test_add_module_records_main_guard(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "runner.py").write_text("if __name__ == '__main__':\n    print('Hello')")
    ctx = FlatteningContext(str(pkg))
    ctx.add_module(pkg / "runner.py")
    assert any("runner" in k for k in ctx.guard_sources)

def test_clash_detection_duplicate_function_names(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("def foo(): pass")
    (pkg / "b.py").write_text("def foo(): pass")
    ctx = FlatteningContext(str(pkg))
    ctx.add_module(pkg / "a.py")
    ctx.add_module(pkg / "b.py")
    with pytest.raises(DuplicateNameError, match=r"Duplicate top-level name: .*"):
        ctx.get_final_output_spans()

def test_ignore_clashes_flag(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("def foo(): pass")
    (pkg / "b.py").write_text("def foo(): pass")
    ctx = FlatteningContext(str(pkg), ignore_clashes=True)
    ctx.add_module(pkg / "a.py")
    ctx.add_module(pkg / "b.py")
    spans = ctx.get_final_output_spans()
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
    with pytest.raises(PathError, match=r"Path .* is not inside package root .*"):
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
            assert spans[i + 1].kind == "blank", "__all__ must be preceded by one blank line"
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

def test_cli_exclude_include(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text('print("PRIMARY")')
    a = pkg / "a"
    a.mkdir()
    (a / "__init__.py").write_text('print("AAA")')
    b = a / "b"
    b.mkdir()
    (b / "__init__.py").write_text('print("BBB")')
    c = a / "c"
    c.mkdir()
    (c / "__init__.py").write_text('print("CCC")')

    # Build flattening context and extract flattened spans
    ctx = FlatteningContext(package_path=pkg, exclude=".a", include=".a.b,.a.c")
    ctx.discover_modules()
    spans = ctx.get_final_output_spans()

    # Flatten into a text buffer
    text = "\n".join(span.text for span in spans)

    assert "PRIMARY" in text
    assert "AAA" not in text
    assert "BBB" in text
    assert "CCC" in text

# __main__ guards

def test_flatten_omit_guards_default(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    f1 = pkg / "a.py"
    f2 = pkg / "b.py"
    f1.write_text("if __name__=='__main__': a=1")
    f2.write_text("if __name__=='__main__': b=2")
    ctx = FlatteningContext(package_path=pkg)
    ctx.add_module(f1)
    ctx.add_module(f2)
    spans = ctx.get_final_output_spans()
    texts = [s.text for s in spans if s.kind=='main_guard']
    assert "a=1" not in "".join(texts) and "b=2" not in "".join(texts)

def test_flatten_includes_requested_guards(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    f1 = pkg / "a.py"
    f2 = pkg / "b.py"
    f3 = pkg / "c.py"
    f1.write_text("if __name__=='__main__': a=1")
    f2.write_text("if __name__=='__main__': b=2")
    f3.write_text("if __name__=='__main__': c=3")
    ctx = FlatteningContext(package_path=pkg, guards_from=".a,.b")
    ctx.discover_modules()
    spans = ctx.get_final_output_spans()
    text = "".join([s.text for s in spans if s.kind=='main_guard'])
    
    assert "a=1" in text
    assert "b=2" in text
    assert "c=3" not in text

def test_flatten_includes_all_guards(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    f1 = pkg / "a.py"
    f2 = pkg / "b.py"
    f3 = pkg / "c.py"
    f1.write_text("if __name__=='__main__': a=1")
    f2.write_text("if __name__=='__main__': b=2")
    f3.write_text("if __name__=='__main__': c=3")
    ctx = FlatteningContext(package_path=pkg, guards_all=True)
    ctx.discover_modules()
    spans = ctx.get_final_output_spans()
    text = "".join([s.text for s in spans if s.kind=='main_guard'])
    
    assert "a=1" in text
    assert "b=2" in text
    assert "c=3" in text

# Needed utility for creating files and triggering discover_modules()
def write(pkg, relpath, content):
    path = pkg / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path

def test_shebang_preserved(tmp_path):
    pkg = tmp_path / "pkg"
    write(pkg, "__init__.py", "x = 1")
    ctx = FlatteningContext(package_path=pkg, shebang="#!test-shebang")
    ctx.discover_modules()
    text = "\n".join(span.text for span in ctx.get_final_output_spans())
    assert ctx.shebang == "#!test-shebang"
    # This validates config but not presence in output yet (feature pending)

def test_clash_with_import_name(tmp_path):
    pkg = tmp_path / "pkg"
    write(pkg, "__init__.py", "from foo import bar\ndef bar(): pass")
    ctx = FlatteningContext(package_path=pkg)
    ctx.discover_modules()
    with pytest.raises(DuplicateNameError, match=r"Duplicate top-level name: .*"):
        ctx.get_final_output_spans()

def test_exclude_with_nested_include_override(tmp_path):
    pkg = tmp_path / "pkg"
    write(pkg, "a/__init__.py", "# excluded")
    write(pkg, "a/b.py", "x = 1")
    write(pkg, "a/c.py", "y = 2")
    ctx = FlatteningContext(package_path=pkg, exclude=".a", include=".a.b")
    ctx.discover_modules()
    text = "\n".join(span.text for span in ctx.get_final_output_spans())
    assert "x = 1" in text
    assert "y = 2" not in text

def test_large_module_set_stress(tmp_path):
    pkg = tmp_path / "pkg"
    for i in range(100):
        write(pkg, f"m{i}.py", f"def f{i}(): pass")
    ctx = FlatteningContext(package_path=pkg)
    ctx.discover_modules()
    spans = ctx.get_final_output_spans()
    functions = [s for s in spans if s.kind == "function"]
    assert len(functions) >= 100

def test_main_from_filters_main(tmp_path):
    pkg = tmp_path / "pkg"
    write(pkg, "cli1/__main__.py", "print('A')")
    write(pkg, "cli2/__main__.py", "print('B')")
    ctx = FlatteningContext(package_path=pkg, main_from="cli1")
    ctx.discover_modules()
    spans = ctx.get_final_output_spans()
    texts = [s.text for s in spans]
    assert any("print('A')" in t for t in texts)
    assert all("print('B')" not in t for t in texts)

def test_invalid_syntax_in_module(tmp_path):
    pkg = tmp_path / "pkg"
    path = write(pkg, "bad.py", "def broken(:\n")  # invalid syntax
    ctx = FlatteningContext(package_path=pkg)
    with pytest.raises(FlatteningError) as e:
        ctx.add_module(path)
    assert isinstance(e.value.__cause__, SyntaxError), "Expected SyntaxError for invalid syntax"    

def test_non_utf8_file_handling(tmp_path):
    pkg = tmp_path / "pkg"
    path = pkg / "binary.py"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b"\xff\xfe\x00bad encoding")
    ctx = FlatteningContext(package_path=pkg)
    with pytest.raises(FlatteningError) as e:
        ctx.add_module(path)
    assert isinstance(e.value.__cause__, UnicodeDecodeError), "Expected UnicodeDecodeError for non-UTF-8 file"

def test_deduplicate_imports(tmp_path):
    pkg = tmp_path / "pkg"
    write(pkg, "__init__.py", "import sys")
    write(pkg, "a.py", "import sys")
    write(pkg, "b.py", "import sys")
    ctx = FlatteningContext(package_path=pkg)
    ctx.discover_modules()
    text = "\n".join(span.text for span in ctx.get_final_output_spans())
    assert text.count("import sys") == 1, "Duplicate imports not deduplicated"

def test_normalize_a_module_name_invalid_type():
    with pytest.raises(FlatteningError):
        normalize_a_module_name(123, "mypkg")  # not a string

def test_normalize_module_names_invalid_type():
    with pytest.raises(FlatteningError):
        normalize_module_names("mypkg", 456)  # not a string or list
