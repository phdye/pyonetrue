# Design.md (Updated)

## Overview

The `FlatteningContext` is responsible for structurally flattening a Python package into a clean, canonical module form. It organizes modules, resolves relative paths, manages main bodies (`__main__.py`), enforces package structure, and ensures clean import and name space integrity.

Recent design updates consolidate and clarify the package flattening process:

---

## FlatteningContext Core Responsibilities

- Accepts an `input_path` (str): either a filesystem path or a dotted module name.
- Resolves and stores:
  - `package_path: Path` (root filesystem path to the package)
  - `package_name: str` (logical dotted name of the package)
- Owns the mapping between source files and flattened module names.
- Provides a method `new_module(path: Path) -> FlatteningModule` to create flattened modules consistently.
- Provides `add_module(path | FlatteningModule)` to add modules into the context.

---

## FlatteningModule

- Created via `FlatteningContext.new_module(path: Path)`.
- Represents a single Python file within the package.
- Stores:
  - `path: Path` — physical file path.
  - `module: str` — canonical dotted name relative to the package root.
- Module name rules:
  - `__init__.py` at package root maps directly to `package_name`.
  - Other `.py` files map to `package_name.submodule...`.
  - Validation ensures every module path is within the package root.

---

## run\_cli\_logic Behavior

- Instantiate `FlatteningContext(opt.input_path)`.
- For each `.py` file under `ctx.package_path`:
  - Create a `FlatteningModule` via `ctx.new_module(file)`.
  - Apply `--include`/`--exclude` filters based on `FlatteningModule.module`.
  - If passing, add module to context via `ctx.add_module(fm)`.

---

## Include/Exclude Semantics

- `--exclude <mod>`:
  - Excludes sub-packages or submodules under `package_name`.
  - `<mod>` is a module path relative to `package_name`.
- `--include <mod>`:
  - Can only be specified **if** `--exclude` exists.
  - Must refer to modules **within** an excluded module.
  - Re-includes selectively inside excluded trees.
- Validation enforced:
  - If `--include` is specified without `--exclude`, raise an error.
  - If an included module is not inside any excluded module, raise an error.
- Evaluation order:
  1. Apply `exclude` first.
  2. Then apply `include` inside the excluded set.

---

## Flattening Rules

- Flattening never jumps outside of `package_name`.
- All flattened modules must reside under `package_name`.
- Flattened module names are canonical, fully dotted paths.
- Imports are normalized and de-duplicated.
- Main guard blocks and `__main__.py` bodies are handled distinctly.
- Function and class name collisions across modules are detected and flagged unless explicitly ignored.

---

## Future Expansion Points

- CLI could support advanced guard/main inclusion options by module pattern.
- Project layouts beyond standard packages (e.g., pyproject.toml-based) could be detected automatically.

---

## Conclusion

These changes ensure a professional, clean, and highly predictable flattening process —
suitable for real-world packaging, module restructuring, and CLI-based automation.

