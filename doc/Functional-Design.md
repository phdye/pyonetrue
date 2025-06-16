# Functional Design

This document summarizes the current implementation of **pyonetrue**, a command-line tool that flattens Python packages into a single self-contained module. It describes the major components, key workflows, and expected behavior based on the repository as it exists today.

## Overview

`pyonetrue` accepts a package directory, Python module, or package name. It parses each source file using Python's `ast` module and reorders the resulting code spans so the output module is deterministic and import-clean. All relative imports are removed, and optional inclusion rules allow injection of main guard blocks or `__main__.py` content.

The tool is primarily executed via `pyonetrue.cli.main` or `python -m pyonetrue`. The CLI options control the flattening context and what entry points are produced.

## Major Components

### CLI (`src/pyonetrue/cli.py`)
- Parses command-line arguments using a docopt-based specification.
- Validates flag combinations and builds a `FlatteningContext` for each entry point.
- Supports flags such as `--module-only`, `--main-from`, `--entry`, `--all-guards`, `--guards-from`, `--exclude`, and `--include`.
- Writes the flattened output either to stdout or to a file/directory.
- Detects entry points from `pyproject.toml` when `--entry` is not provided.
- `--shebang` allows specifying a custom interpreter line when including `__main__.py`.
- `--show-cli-args` prints the resolved arguments and exits.

### FlatteningContext (`src/pyonetrue/flattening.py`)
- Core object orchestrating the flattening pipeline.
- Resolves the package path or module path and infers `package_name`.
- Discovers source modules via `discover_modules()` while honoring exclude/include filters and which `__main__.py` files may be used.
- Collects spans from each file using `extract_spans` and stores them for later assembly.
- Aggregates main guard spans and the chosen `__main__.py` content.
- Normalizes imports and assembles final output spans with `get_final_output_spans()`.
- Detects duplicate top-level definitions unless `ignore_clashes` is set.
- Stores spans per module in `module_spans` and main guard locations in `guard_sources`.
- Provides helper methods like `gather_root_spans()` and `gather_main_guard_spans()` before final assembly.

### FlatteningModule (`src/pyonetrue/flattening.py`)
- Represents one source file within the context.
- Computes the canonical dotted module name relative to the package root.
- Ensures a provided path is actually under the package root.

### AST Extraction (`src/pyonetrue/extract_ast.py`)
- Parses each file via `ast.parse` and converts nodes to `Span` objects.
- Each `Span` records the raw source text and its kind (`import`, `class`, `function`, `logic`, or `main_guard`).
- Spans retain original order and include decorator lines when applicable.
- Detects `if __name__ == "__main__"` blocks and labels them as `main_guard`.

### Import Normalization (`src/pyonetrue/normalize_imports.py`)
- Eliminates all relative imports and local absolute imports.
- Deduplicates imports and groups them into standard library versus third‑party.
- Provides helpers `format_plain_import` and `format_from_import` for final formatting.
- Returns the list of normalized `Span` objects along with the imported symbol names used for clash detection.

### Exceptions (`src/pyonetrue/exceptions.py`)
- Defines custom error types including `CLIOptionError`, `DuplicateNameError`, `ImportNormalizationError`, `IncludeExcludeError`, `FlatteningError`, `ModuleInferenceError`, and `PathError`.
- These exceptions are raised during option validation, parsing, or pipeline stages to signal configuration or structural issues.

## Processing Pipeline
1. **Input Resolution** – `FlatteningContext` determines whether the path is a directory, file, or package name and stores the canonical package root.
2. **Module Discovery** – Source files under the root are collected in sorted order. Inclusion rules decide which modules or subpackages are flattened and whether `__main__.py` from a submodule should be used.
3. **Span Extraction** – Each file is parsed into ordered `Span` objects. Main guard blocks are recorded separately so they can be included or omitted later.
4. **Gathering** – Root-level docstring, `__all__` declaration, imports, and other logic are gathered. Non-root module spans are also collected, except for main guards which may be aggregated separately.
5. **Span Organization** – `gather_root_spans`, `gather_module_spans`, and `gather_main_guard_spans` collect categorized spans for later assembly.
6. **Import Normalization** – All collected import spans are run through `normalize_imports` to rewrite, deduplicate, and group them.
7. **Assembly** – `normalize_and_assemble` arranges docstring, future imports, regular imports, optional `__all__`, classes, functions, top-level logic, chosen main guard blocks, and optionally `__main__.py`. Blank lines are inserted to maintain readability.
8. **Clash Detection** – `check_clashes` verifies that top-level functions and classes do not share names with each other or with imported symbols unless `ignore_clashes` is specified.
9. **Output Generation** – The resulting spans are concatenated to produce the final module text, optionally prefixed with a shebang if `__main__.py` is included.

## Handling of Entry Points
Supplying `--module-only` suppresses all entry-point logic -- incompatible with all other entry point options.

<u>No Script Entry Points</u>

- By default, only the package's primary `__main__.py` is eligible for inclusion.  
- The `--main-from` option specifies a sub-package that provides the `__main__.py` body instead.
- Supplying `--module-only` suppresses all default entry-point logic.
- Guard blocks (`if __name__ == '__main__'`) are discarded unless `--all-guards` or `--guards-from` is used. Guards can be selected from specific modules or from every module in the package.

<u>Has Script Entry Points</u>

- If a package has script entry points and no entry point options are specified, each script entry point is generated as if the user had specified `--entry <name>` for each one.
- The `--entry <name>` option builds a module tailored for a script entry point `<name>` as found by `importlib.metadata.entry_points()`.  Each such `--entry` is processed independently so multiple CLIs can be generated in one invocation.  If entry points specify the same function name to invoke (e.g. `main`, `app`, `foobar`), each entry point single module produced will not include the other entry point modules.

## Import Rules
- Relative imports (`from .foo import bar`) are removed entirely.
- Absolute imports that reference the same package (`import pkg.sub` or `from pkg import sub`) are also removed to keep the output self-contained.
- Remaining imports are deduplicated and sorted such that standard library imports appear before third‑party imports, with a blank line separating the groups.

## Error Policies
- Invalid CLI flag combinations raise `CLIOptionError` early in the CLI workflow.
- Syntax errors or encoding problems while parsing a file are wrapped in `FlatteningError` so the user knows which module failed.
- Duplicate class or function names across modules raise `DuplicateNameError` unless `--ignore-clashes` is used.

## Example Workflow
1. User runs `pyonetrue src/mypkg --output flat/mypkg.py`.
2. The CLI creates a `FlatteningContext` pointing at `src/mypkg`.
3. Modules are discovered in sorted order under `src/mypkg`.
4. Spans are extracted, imports normalized, and all code pieces are assembled into a single list of spans.
5. The output file is written, containing docstrings, deduplicated imports, class and function definitions, and optional entry-point logic depending on the flags.

## Summary
The current implementation of **pyonetrue** provides a deterministic, AST‑based approach to flattening Python packages. A combination of explicit CLI options and strict processing ensures the resulting module is both syntactically valid and free of unwanted relative imports. Custom errors and an extensive test suite enforce correct behavior across a wide range of scenarios. This architecture allows the tool to be used for reproducible builds, packaging simplification, and CLI preparation.
