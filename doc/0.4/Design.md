# pyonetrue Design Document (Version 0.4.0 — Ground-Up Redesign)

## Purpose

`pyonetrue` is a CLI tool that flattens one or more Python modules and packages into a single well-structured output module. It supports top-level span reordering, import normalization, and precise handling of entrypoints, including explicit support for `__main__.py`.

Unlike version 0.3.0, which treated the input as a monolithic source buffer, version 0.4.0 introduces a **structured flattening pipeline** where each module is analyzed and composed independently, then merged according to user directives.

---

## High-Level Objectives

- ✅ Produce a fully ordered, executable Python module from:
  - Packages
  - Individual `.py` files
  - Mixed sets of inputs
- ✅ Normalize and deduplicate imports
- ✅ Preserve relative ordering of classes, functions, and logic
- ✅ Treat `__main__.py` as a special case: **not reordered**, only cleaned and appended
- ✅ Allow user-directed inclusion of `if __name__ == '__main__'` blocks
- ✅ Compose result from **structured module parts**, not a concatenated buffer
- ✅ Detect and error on top-level name clashes unless explicitly ignored

---

## Architectural Overview

Each input module is:
1. Parsed into a list of `CodeSpan` objects via `cleanedit.analyze_source()`
2. Tagged with its origin (path, module name, or user label)
3. Grouped into structural parts: imports, classes, functions, logic, main guards

The reordering process happens at the **module level**, then the results are stitched together respecting the global policy:
- Import cleanup occurs across **all modules**
- `__main__.py` is isolated early, cleaned separately, and appended last
- Any chosen `main` guard is appended last (if explicitly included)
- Symbol names are checked for duplicates unless `--ignore-clashes` is specified

---

## Key Concepts

### Structural Flattening (not buffer flattening)
Each module is treated as a source of **semantic spans**, not a blob of source. This enables correct handling of:
- Global name conflicts
- Contextual span preservation (e.g., decorators)
- Fine-grained ordering control

### Special Handling: `__main__.py`
- All import spans are extracted and cleaned
- All other spans are preserved **in original order**
- The result is appended **after all reordered content**

### Main Guard Logic
Main guards (`if __name__ == '__main__':`) are treated as:
- Ignored by default
- Optionally included from:
  - A specific file (`--main-from file.py`)
  - A specific module (`--main-from p.module`)
  - All files (`--main-all`)

Only **one** main block is permitted in output. Conflicting options trigger an error.

---

## CLI Interface

```
Usage:
  pyonetrue [options] <inputs>...

Options:
  --output=<file>      Write flattened output to file
  --stdout             Write flattened output to stdout
  --main-all           Include all if __name__ == '__main__' blocks
  --main-from <mod>    Include main block from specified module or file
  --omit-main          Discard all main guards (default)
  --ignore-clashes     Allow duplicate top-level names without error
  --ignore-errors      Allow partially malformed files to be processed
  -h, --help           Show help
  --version            Show version
```

---

## Processing Pipeline

1. **Input Collection**
   - Resolve paths and modules from CLI
   - Classify into `.py` files, packages, or virtual inputs

2. **Module Analysis (per file)**
   - Load source
   - Extract spans
   - Tag origin (for later filtering, e.g. `--main-from`)

3. **Span Classification**
   - Split into:
     - `imports`
     - `classes`
     - `functions`
     - `orphans` (top-level logic)
     - `main_guards`

4. **Import Normalization**
   - All imports from all modules are deduplicated
   - Grouped into stdlib, third-party, local (black-style)

5. **Content Assembly**
   - Ordered:
     1. Normalized imports
     2. Reordered top-level spans (excluding main guards)
     3. Selected main block (if any)
     4. Cleaned `__main__.py` (original order, imports normalized only)

6. **Top-Level Symbol Collision Detection**
   - Raise error if any class/function names collide across modules
   - Suppress with `--ignore-clashes`

7. **Output Rendering**
   - Render all selected spans into final module string
   - Write to file or stdout

---

## Output Rules

- All import spans appear at the top
- No duplicate top-level definitions (unless `--ignore-clashes` used)
- Only one main block may appear (either from a file or `__main__.py`)
- `__main__.py` content always appears last and is not reordered

---

## Future Enhancements

- [ ] Top-level name deduplication with rename hints
- [ ] AST-level merge conflict resolution
- [ ] Cross-module symbol references and inlining
- [ ] Source map / trace output for diagnostics

---

## Version Status

This document specifies version 0.4.0 of `pyonetrue`, which introduces structured multi-module flattening, `__main__.py` awareness, and span-based composition. It replaces the 0.3.x buffer-oriented approach.
