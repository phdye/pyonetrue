# pyonetrue Design Document (Version 0.3.0)

## Overview

`pyonetrue` is a CLI utility that flattens Python packages or modules into a cleanly ordered source file. It supports structural normalization, import cleanup, and optional removal of `if __name__ == '__main__'` blocks.

The primary use case is for generating well-structured, single-module outputs from larger packages, suitable for distribution, testing, or direct execution.

---

## Objectives

- ✅ Flatten a package into a single Python file
- ✅ Normalize top-level structure: imports, classes, functions, logic blocks
- ✅ Group and sort imports by PEP8 / black conventions
- ✅ Provide CLI flags to optionally remove `__main__` blocks

---

## Key Concepts

### Span-Based Reordering
`pyonetrue` relies on `cleanedit` to extract spans from source files. Each top-level span represents a structural unit:

- `import` or `from` statements
- Class and function definitions
- Main guard blocks
- Orphan statements (e.g. top-level logic)

These spans are then grouped and reordered to match a consistent top-down structure:

1. `__future__` imports (original order)
2. All other imports (normalized and deduplicated)
3. Class definitions
4. Function definitions
5. Other logic blocks (e.g. top-level expressions)
6. `if __name__ == "__main__"` block (if not omitted)

### Main Guard Handling
By default, main guard blocks are **included** in the output. However, the user can request they be omitted by passing either:

- `--omit-main`
- `--module` (which implies `--omit-main = True`)

This applies globally to all modules. There is no per-module selection or recognition of `__main__.py`.

### Output Modes
- **Script Mode (default)**: Includes all spans, including `__main__` guards
- **Module Mode**: Strips all `__main__` blocks for pure importable output

---

## CLI Interface

Defined via `docopt()` and located at `scripts/pyonetrue`.

```
Usage:
  pyonetrue <input_file_or_package> [--output=<file>] [--module] [--omit-main]
  pyonetrue -h | --help
  pyonetrue --version

Options:
  -h --help         Show this screen.
  --version         Show version.
  --output=<file>   Write result to <file> [default: stdout]
  --module          Output in pure module mode (no __main__ block)
  --omit-main       Remove any if __name__ == '__main__' block
```

---

## Flattening Strategy

1. If input is a **single file**, treat it as a module
2. If input is a **directory/package**, use `flatten_package_to_buffer()` to collect and concatenate its contents
3. Analyze the combined source via `analyze_source()`
4. Extract and reorder spans via `reorder_top_level_spans()`
5. Rebuild the flattened output from the resulting spans

---

## Special Handling

- All imports are normalized via `normalize_import_spans()`
- Main blocks are only removed if `--omit-main` or `--module` is passed
- `__main__.py` is not treated specially in version 0.3.0
- All source files are processed equally based on flags

---

## Future Enhancements

- [ ] Treat `__main__.py` as a special case (preserve body, clean imports only)
- [ ] Add `--include-main <module>` for selective main guard retention
- [ ] Output flattened source map or trace metadata
- [ ] Preserve comments and docstrings across all spans

---

## Status

Current CLI version: `0.3.0`
Stable for module and script flattening based on global omit-main behavior.
No file-level exceptions or structural introspection yet implemented.