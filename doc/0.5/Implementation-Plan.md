# Implementation Plan for `pyonetrue` v0.5.0

This plan outlines the sequence of work needed to realize the simplified, syntax-only design of `pyonetrue` v0.5.0, which assumes that all input modules parse cleanly and omits error-recovery logic.

---

## Phase 1: Remove Error-Recovery & Placeholder Logic

1. **Prune recovery modules**
   - Delete or deprecated: `recover_ast_spans()`, `invalid` placeholder span generation, and any `--ignore-errors` handling in CLI.  
2. **Strip fallback branches**
   - In `analyze_source()`, remove try/catch blocks that catch `SyntaxError` and insert dummy spans.  
   - Eliminate `ValidationEngine` calls tied to parse recovery (patch-level validation may remain for edit safety but is no longer required for parsing).  
3. **Clean up imports**
   - Remove imports of recovery-specific helpers (e.g. `compile_command` fallbacks).  

## Phase 2: Simplify Core AST Pipeline

1. **Single-path parsing**  
   - Ensure `analyze_source()` uses `ast.parse()` directly on raw source text.  
2. **Span generation fidelity**  
   - Verify that every line in the source is mapped to a `CodeSpan` derived from real AST nodes or safe default spans (no synthetic placeholders).  
3. **Consolidate classification**  
   - Refactor span-classification logic into a single module (e.g. `span_classifier.py`) that assumes valid AST.  
4. **Update data models**  
   - Remove any `Span.kind == 'invalid'` variants; simplify `CodeSpan` metadata to only reflect semantic categories: `import`, `class`, `function`, `logic`, `main_guard`.

## Phase 3: CLI Flag & Help Text Adjustments

1. **Remove `--ignore-errors` option**  
   - Delete flag parsing, help text, and internal conditionals that check for error tolerance.  
2. **Version bump**  
   - Update `__version__` to `0.5.0` in `pyonetrue/__init__.py`.  
3. **Help & documentation**  
   - Adjust CLI `--help` output to reflect dropped flag.  
   - Ensure default behavior (`--omit-main`) remains unchanged.  

## Phase 4: Testing & Validation

1. **Prune invalid-input tests**  
   - Remove or skip tests that intentionally feed malformed Python or assert placeholder recovery.  
2. **Augment core-path tests**  
   - Add tests verifying direct `analyze_source()` on valid modules produces correct spans for every line.  
3. **CLI regression tests**  
   - Update tests that covered `--ignore-errors` to expect its absence.  
4. **Full test run**  
   - Execute `pytest` under clean PYTHONPATH; ensure zero failures and coverage remains high for all semantic behaviors.  

## Phase 5: Documentation & Release Notes

1. **README & docs**  
   - Remove sections describing error recovery and placeholder spans.  
   - Clearly state that all inputs must parse without errors.  
2. **CHANGELOG.md**  
   - Add entry for v0.5.0, noting removal of recovery, `--ignore-errors`, and simplified single-path pipeline.  
3. **User migration guide**  
   - Brief note for existing users about handling parse errors before flattening (e.g., run linters/pre-commit).  

## Phase 6: Release & Packaging

1. **Tag & Publish**  
   - Create Git tag `v0.5.0`.  
   - Build and publish distribution artifacts (e.g., PyPI).  
2. **Archive build**  
   - Generate `pyonetrue.zip` and update baseline if needed.  

---

*Progress through these phases sequentially, running tests after each major change.*

