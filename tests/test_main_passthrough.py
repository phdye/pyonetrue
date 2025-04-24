from cleanedit import analyze_source
from pyonetrue.flattening import FlatteningContext

def test_main_py_passthrough_behavior(tmp_path):
    # Create __main__.py with import and body
    main_py = tmp_path / "__main__.py"
    main_py.write_text("""\
import sys
print("Hello from main")
""")

    # Create a normal module
    mod_py = tmp_path / "mod.py"
    mod_py.write_text("""\
import os

def foo():
    return 42
""")

    ctx = FlatteningContext()
    ctx.add_module(str(mod_py))
    ctx.add_module(str(main_py))

    spans = ctx.get_final_output_spans()
    lines = [s.text.strip() for s in spans]

    print("DEBUG LINES:", lines)

    assert "import os" in lines
    assert "import sys" in lines
    assert any("def foo" in line for line in lines)
    assert any("print(\"Hello from main\")" in line for line in lines)

    # Ensure __main__.py body is at the end
    main_start = lines.index("import sys")
    body_index = lines.index("print(\"Hello from main\")")
    assert body_index > main_start

def test_main_py_passthrough_behavior_syntax_error(tmp_path):
    # Create __main__.py with import and body
    main_py = tmp_path / "__main__.py"
    main_py.write_text("""\
import sys
print("Hello from main")
""")

    # Create a normal module
    mod_py = tmp_path / "mod.py"
    mod_py.write_text("""\
import os

def foo():
return 42
""")

    ctx = FlatteningContext()
    ctx.add_module(str(mod_py))
    ctx.add_module(str(main_py))

    spans = ctx.get_final_output_spans()
    lines = [s.text.strip() for s in spans]

    print("DEBUG LINES:", lines)

    assert "import os" in lines
    assert "import sys" in lines
    assert any("def foo" in line for line in lines)
    assert any("print(\"Hello from main\")" in line for line in lines)

    # Ensure __main__.py body is at the end
    main_start = lines.index("import sys")
    body_index = lines.index("print(\"Hello from main\")")
    assert body_index > main_start
