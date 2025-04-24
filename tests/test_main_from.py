from pyonetrue.flattening import FlatteningContext

def test_main_from_behavior(tmp_path):
    mod = tmp_path / "foo.py"
    mod.write_text("""\
import os

def foo(): return 1

if __name__ == '__main__':
    print('hello main')
""")

    ctx = FlatteningContext()
    ctx.add_module(str(mod))
    ctx.set_main_from(str(mod))

    spans = ctx.get_final_output_spans()
    texts = [s.text.strip() for s in spans]
    print("DEBUG LINES:", texts)

    assert "import os" in texts
    assert any("def foo" in t for t in texts)
    assert any("print('hello main')" in t for t in texts)
