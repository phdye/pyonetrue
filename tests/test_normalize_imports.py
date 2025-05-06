import pytest

from pyonetrue import Span
from pyonetrue import (
    normalize_imports,
    format_plain_import,
    format_from_import,
    is_stdlib_module,
    set_line_length,
    get_line_length,
    ImportEntry,
    ImportNormalizationError,
)

# Helper for building simple import spans
def imp(text):
    return Span(text=text, kind="import")

def test_import_entry_instantiation():
    entry = ImportEntry(module="os", symbol=None, asname="o", is_plain_import=True)
    assert entry.module == "os"
    assert entry.symbol == ""
    assert entry.asname == "o"
    assert entry.is_plain_import is True

def test_format_plain_import_basic():
    entry1 = ImportEntry(module="os", symbol=None, asname=None, is_plain_import=True)
    entry2 = ImportEntry(module="os", symbol=None, asname="o", is_plain_import=True)
    result = format_plain_import([entry1, entry2])
    assert result[0] == "import os"
    assert result[1] == "import os as o"
    
def test_format_from_import_basic():
    entry1 = ImportEntry(module="os", symbol="path", asname=None, is_plain_import=False)
    entry2 = ImportEntry(module="os", symbol="getenv", asname="env", is_plain_import=False)
    result = format_from_import([entry1, entry2])
    assert result[0] == "from os import getenv as env, path"
    assert len(result) == 1

def test_is_stdlib_module_basic():
    assert is_stdlib_module("os") is True
    assert is_stdlib_module("sys") is True
    assert is_stdlib_module("requests") is False
    assert is_stdlib_module("six") is False

def test_set_and_get_line_length():
    old_length = get_line_length()
    set_line_length(120)
    assert get_line_length() == 120
    set_line_length(old_length)  # restore after test

def test_invalid_line_length_setting():
    with pytest.raises(ImportNormalizationError, match=r"`line_length` must be > 0"):
        set_line_length(0)
    with pytest.raises(ImportNormalizationError, match=r"`line_length` must be > 0"):
        set_line_length(-10)

def test_basic_simple_import():
    spans = [imp("import os")]
    normalized, _ = normalize_imports("pkg", spans)
    assert any("import os" in s.text for s in normalized)

def test_basic_from_import():
    spans = [imp("from os import path")]
    normalized, _ = normalize_imports("pkg", spans)
    assert any("from os import path" in s.text for s in normalized)

def test_eliminate_relative_import():
    spans = [imp("from .foo import bar"), imp("from .. import baz")]
    normalized, _ = normalize_imports("pkg", spans)
    assert len(normalized) == 0

def test_deduplicate_same_import():
    spans = [imp("from os import path"), imp("from os import path")]
    normalized, _ = normalize_imports("pkg", spans)
    texts = [s.text for s in normalized]
    assert texts.count("from os import path\n") == 1

def test_group_stdlib_and_third_party():
    spans = [imp("import os"), imp("import requests")]
    normalized, _ = normalize_imports("pkg", spans)
    text = "\n".join(s.text for s in normalized)
    # Check blank line between groups
    assert "import os" in text
    assert "import requests" in text
    assert "\n\n" in text  # group separator

def test_long_from_import_vertical_formatting():
    symbols = ", ".join(f"name{i}" for i in range(20))
    spans = [imp(f"from module import {symbols}")]
    normalized, _ = normalize_imports("pkg", spans)
    text = "\n".join(s.text for s in normalized)
    assert "(\n" in text and ",\n" in text

def test_third_party_vs_stdlib_heuristic():
    spans = [imp("import six"), imp("import os")]
    normalized, _ = normalize_imports("pkg", spans)
    text = "\n".join(s.text for s in normalized)
    assert "import os" in text
    assert "import six" in text
    assert "\n\n" in text

def test_no_imports():
    spans = []
    normalized, _ = normalize_imports("pkg", spans)
    assert normalized == []

def test_unicode_import_symbol():
    spans = [imp("from foo import αβ")]
    normalized, _ = normalize_imports("pkg", spans)
    assert any("αβ" in s.text for s in normalized)

def test_no_deduplicate_import_alias():
    spans = [imp("import os as o"), imp("import os")]  # same real module
    normalized, _ = normalize_imports("pkg", spans + spans)
    text = "\n".join(s.text for s in normalized)
    # Should de-duplicate the second copy of each import
    # Should not de-duplicate 'os' vs 'os as o', different imported symbol
    assert text.count("import os\n") == 1
    assert text.count("import os as o\n") == 1

def test_deduplicate_imports():
    spans = [imp("import sys"), imp("import os")]  # same real module
    normalized, _ = normalize_imports("pkg", spans + spans)
    text = "\n".join(s.text for s in normalized)
    # Should de-duplicate the second copy of each import
    assert text.count("import sys\n") == 1
    assert text.count("import os\n") == 1

def test_import_clash():
    # Clash: importing "path" from two different modules should raise
    spans = [
        imp("from os import path"),
        imp("from custom import path"),
    ]
    with pytest.raises(ImportNormalizationError, match=r"name clash importing .* from .*, already imported from .*"):
        normalize_imports("pkg", spans)

def test_is_stdlib_module_basic():
    assert is_stdlib_module("os") is True
    assert is_stdlib_module("sys") is True
    assert is_stdlib_module("math") is True
    assert is_stdlib_module("requests") is False
    assert is_stdlib_module("six") is False
    assert is_stdlib_module("numpy") is False

def test_preserve_plain_import_format():
    spans = [imp("import os")]
    normalized, _ = normalize_imports("mypkg", spans)
    assert any(span.text == "import os\n" for span in normalized)

def test_preserve_from_import_format():
    spans = [imp("from os import path")]
    normalized, _ = normalize_imports("mypkg", spans)
    assert any(span.text.startswith("from os import path") for span in normalized)

def test_preserve_import_alias_format():
    spans = [imp("import os as o")]
    normalized, _ = normalize_imports("mypkg", spans)
    assert any(span.text.startswith("import os as o") for span in normalized)

def test_preserve_from_import_alias_format():
    spans = [imp("from os import path as p")]
    normalized, _ = normalize_imports("mypkg", spans)
    assert any(span.text.startswith("from os import path as p") for span in normalized)

