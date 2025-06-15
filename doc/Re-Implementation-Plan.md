# Implementation Plan for `pyonetrue` v0.5.4

This plan refocuses **pyonetrue** on its compiler-like mission: _flatten valid Python modules into a unified, executable whole,_ using **`ast.parse()`** for span extraction rather than the CleanEdit library.

---

## Phase 1: Remove CleanEdit Dependency & Implement AST-Based Extraction

1. **Purge CleanEdit imports**  
   - In `src/pyonetrue/flattening.py`, `src/pyonetrue/__main__.py`, and `scripts/pyonetrue`, remove:
     ```python
     from cleanedit import analyze_source, rebuild_source_from_spans
     ```
   - Remove any CleanEdit-related dependencies from `setup.py` or `pyproject.toml`.
2. **Implement pure-AST extractor**  
   - Create a new module `src/pyonetrue/extract_ast.py` with functions that:
     - Parse source via `ast.parse(source, filename)`
     - Walk the AST to collect top-level `Import`, `ImportFrom`, `ClassDef`, `FunctionDef`, and `If` nodes matching `__main__` guards
     - Use `ast.get_source_segment(source, node)` to grab exact text for each node
     - Preserve node order from the original file
3. **Replace `analyze_source()` calls**  
   - In flattening.py and CLI entrypoints, invoke the new AST extractor instead of CleanEdit’s API:
     ```python
     from pyonetrue.extract_ast import extract_spans
     spans = extract_spans(source)
     ```
4. **Update packaging metadata**  
   - Remove CleanEdit from install_requires
   - Ensure minimum Python version supports `ast.get_source_segment()` (>=3.8)

## Phase 2: CLI Flag & Help Text Refinement

- Implement elimination of all relative imports during flattening.
- Ensure flattened modules contain no relative (`.`) imports.

1. **Flag renaming & additions**  
   - Confirm `--omit-main` is present; remove `--module` if redundant.  
   - Add `--main-all`, `--main-from <module>`, and `--ignore-clashes` flags.  
2. **Usage & Documentation**  
   - Revise docstrings in `__main__.py` and `scripts/pyonetrue` to reflect the new AST approach and flags.  
   - Remove any mention of recovery or validation flags like `--trace` if it no longer applies.
3. **Flag propagation**  
   - Wire new flags through to the core flattening functions (`flatten_package_to_buffer` or similar).

## Phase 3: Testing & Validation

1. **Remove recovery tests**  
   - Delete or xfail tests under `tests/cleanedit/` and any tests expecting fallback behavior.  
2. **AST extractor tests**  
   - Create unit tests in `tests/pyonetrue/test_extract_ast.py` to:
     - Verify imports, classes, functions, and main guards are correctly extracted
     - Ensure `ast.get_source_segment` preserves formatting for simple examples
3. **CLI tests for flags**  
   - Under `tests/pyonetrue/`, add tests for `--omit-main`, `--main-all`, `--main-from`, and `--ignore-clashes` behaviors.
4. **Regression flattening tests**  
   - Keep existing tests for `classify`, `normalize`, `reorder`, etc., but modify them to use AST spans instead of CodeSpan objects.

## Phase 4: Version Bump & Documentation

1. **Bump version**
   - Set `__version__ = '0.5.4'` in `src/pyonetrue/__init__.py`.
2. **Update README & CHANGELOG**  
   - Document the shift to AST-based extraction and removal of CleanEdit dependency.
3. **Migration notes**  
   - Advise users to ensure their code is syntactically valid (e.g., via linters or `python -m py_compile`).

## Phase 5: Release & Packaging

1. **Tag release**
   - Create Git tag `v0.5.4` in the **pyonetrue** repo.
2. **Publish package**  
   - Build and upload to PyPI or internal index.
3. **Archive snapshot**  
   - Produce `pyonetrue.zip` for distribution.

---

*Proceed through each phase in order, validating tests after each major change to maintain stability.*

