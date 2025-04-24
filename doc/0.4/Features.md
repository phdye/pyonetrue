# pyonetrue Features Document

## Overview

`pyonetrue` is a CLI utility that flattens Python packages or modules into a cleanly ordered source file. It supports structural normalization, import cleanup, and customizable treatment of script entry points.

The primary use case is for generating well-structured, single-module outputs from larger packages, suitable for distribution, testing, or direct execution.

---

## Objectives

- ✅ Generate a well ordered, functional, single file Python module from :
  - Python package specified by name - incorporating all constituent modules
  - Single unordered Python module -- potentially flattened by a prior process via simple concatenation
  - List of individual modules
  - or a any combination of the above
- ✅ Normalize top-level structure: imports, classes, functions, logic blocks
- ✅ Group and sort imports by PEP8 / black conventions
- ✅ Provide CLI flags to control output behavior
- ✅ Strip or preserve `__main__` blocks based on CLI intent, strip is the default.
- [ ] Treat `__main__.py` specially (append its body, no reordering)
- [ ] Add `--main-from <module>` include `__main__` block from <module>
- [ ] Optionally, provide a custom entry point
- [ ] Optionally, disregard all syntax errors
- [ ] Optionally, ignore name clashes when `--ignore-clashes` is used

---

## Required Characteristics

- ✅ No global name clashes (unless `--ignore-clashes` specified)
- ✅ No syntax errors -- unless disregarded

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
6. `if __name__ == "__main__"` block (if included)

### Main Guard Handling
By default, all main guard blocks are rem. They are only preserved if explicitly requested via:

- `--include-main` in the future
- `--module` (implies `--omit-main = True`)

Special case:
- The body of `__main__.py` is **not reordered**. It is appended as-is, with import cleanup only.

### Output Modes
- **Module Mode**: Strips all CLI entrypoint logic (pure importable module)
- **Script Mode**: Preserves the designated main block (if applicable)

---

## CLI Interface

Defined via `docopt()` and located at `scripts/pyonetrue`.

```
Usage:
  pyonetrue [options] <input>...
  pyonetrue -h | --help
  pyonetrue --version

Options:
  --output=<file>      Write resulting module to <file>
  --stdout             Write resulting module to STDOUT
  --main-all           Include all `if __name__ == '__main__'` blocks
  --main-from <m>      Package, module, or file name to include `'__main__'` block from
  --omit-main          Do not include __main__.py or any `'__main__'` blocks
  --ignore-clashes     Allow name collisions without raising errors
  -h, --help           Show this screen.
  --version            Show version.
```

---

## Flattening Strategy

1. If input is a **single file**, treat it as a module
2. If input is a **directory/package** walk to gather files contents into a single module
3. If multiple inputs, concatenate in order into a single module
4. Analyze the combined source via `analyze_source()`
5. Extract and reorder spans via `reorder_top_level_spans()`
6. Detect name clashes between top-level symbols; raise error unless `--ignore-clashes` specified
7. Rebuild the flattened output from the resulting spans
8. Append `'__main__.py'` or specified `'__main__'` blocks
 
---

## Special Handling

- All imports are normalized via `normalize_import_spans()`
- Main blocks are only retained when explicitly requested
- `__main__.py`'s body is appended but never reordered
- The resulting file is either printed or saved via `--output`

---

## Future Enhancements

- [ ] Output flattened source map or trace metadata
- [ ] Preserve comments and docstrings across all spans

---

## Status

Current CLI version: `0.4.0`
Stable for module flattening and test packaging.
Actively evolving to support strict main logic rules and better package introspection.
