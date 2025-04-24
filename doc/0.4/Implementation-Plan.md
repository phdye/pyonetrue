**Implementation Plan for `pyonetrue` v0.4+**

This implementation plan outlines the tasks and sequencing needed to complete the design described in `pyonetrue-design-0.4.md`. The work is divided into functional domains and aligned with the CLI interface and structural guarantees.

---

## Phase 1: Core Feature Completion

### 1. Handle `__main__.py` Body (No Reordering)
- [ ] Detect and extract body of `__main__.py`
- [ ] Clean up imports within `__main__.py`
- [ ] Append cleaned body to the end of final output
- [ ] Exclude from reorder span logic

### 2. Implement `--main-from <module>`
- [ ] Accept module or file name
- [ ] Locate and extract `if __name__ == "__main__"` block
- [ ] Strip all other `__main__` blocks
- [ ] Append chosen block after reordering

### 3. Add CLI Flag Parsing Logic
- [x] Accept multiple input paths
- [x] Support `--stdout`, `--output`
- [x] Support `--omit-main`
- [ ] Implement `--main-from <module>`
- [ ] Implement `--main-all`


---

## Phase 2: Span Extraction and Reordering

### 4. Ensure CleanEdit Span Fidelity
- [x] Every line in input must be part of a span
- [x] No line skipping or accidental truncation
- [x] Preserve order of `__future__` imports

### 5. Reordering Logic (already functional, verify against spec)
- [x] `__future__` imports
- [x] Other imports (normalized, deduped)
- [x] Classes
- [x] Functions
- [x] Orphan logic blocks
- [ ] Conditional main block (from flags)


---

## Phase 3: Package and File Handling

### 6. Accept and Flatten Arbitrary Input Combinations
- [x] Single file
- [x] Multiple `.py` files
- [x] Python package (directory)
- [ ] Mix of files and directories
- [ ] De-duplicate loaded module content if same file given twice

### 7. Integrate Main Guard Processing into Pipeline
- [ ] Remove all `if __name__ == '__main__'` blocks by default
- [ ] Retain only selected block from `--main-from` or `--main-all`
- [ ] Never reorder `__main__.py`, only append


---

## Phase 4: Import Cleanup and Normalization

### 8. Finalize `normalize_import_spans()`
- [x] Group `import` and `from` imports
- [ ] Deduplicate imports
- [ ] Expand star imports (if feasible)
- [ ] Expand multi-symbol imports into one per line (if enabled)

### 9. Import Cleanup Modes (future option set)
- [ ] `--dedupe-imports`
- [ ] `--expand-imports`
- [ ] `--split-symbols`


---

## Phase 5: Testing, Validation, CLI Polish

### 10. Comprehensive Unit Tests
- [x] Test `reorder_top_level_spans()`
- [x] Test `normalize_import_spans()`
- [x] CLI flatten single file
- [ ] CLI flatten package
- [ ] CLI flatten multi-source
- [ ] CLI `--main-from` and `--main-all` tests
- [ ] `__main__.py` passthrough tests

### 11. Edge Cases & Fuzzing
- [ ] File with only `__main__`
- [ ] Empty modules
- [ ] Duplicate symbol names across modules
- [ ] Mixed import styles


---

## Phase 6: Metadata and Source Maps

### 12. Optional Output Metadata (for future tooling)
- [ ] Span index to original files
- [ ] Hash or checksum for every span
- [ ] Output `.map` or `.json` metadata alongside flattened source


---

## Final Deliverables

- [ ] Fully functioning CLI at `scripts/pyonetrue`
- [ ] Tests under `tests/pyonetrue/`
- [ ] Updated version header: `pyonetrue.__version__ = '0.4.X'`
- [ ] Documentation updates:
  - `README.md`
  - CLI usage doc
  - Span behavior and main guard rules

