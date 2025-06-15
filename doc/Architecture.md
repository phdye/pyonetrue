# Architecture Overview

Version: **0.8.0**
Status: **Draft**

This document outlines the high-level design of **pyonetrue**. It focuses on the major components, their responsibilities, and how they interact when flattening Python packages into a single module.

## Major Components

### CLI (`src/pyonetrue/cli.py`)
* Parses command line options using **docopt**.
* Validates flags and constructs a `FlatteningContext` for each requested entry point.
* Delegates flattening to the context and writes output to the target file or stdout.

### FlatteningContext (`src/pyonetrue/flattening.py`)
* Central object that orchestrates the flattening process.
* Discovers modules from the package path, applying include/exclude rules.
* Collects `Span` objects from each module via `extract_spans`.
* Gathers main guard blocks and the desired `__main__.py` body.
* Normalizes imports and assembles ordered spans for output.
* Detects duplicate top-level names unless `--ignore-clashes` is set.

### FlatteningModule
* Represents a single Python file in the context.
* Computes the fully qualified module name relative to the package root.
* Provides a convenient wrapper for adding modules to the context.

### AST Extractor (`src/pyonetrue/extract_ast.py`)
* Parses source files with `ast.parse`.
* Produces a sequence of `Span` objects classified as imports, classes, functions, logic, or main guards.

### Import Normalizer (`src/pyonetrue/normalize_imports.py`)
* Rewrites relative imports to absolute form and removes local absolute imports.
* Deduplicates and groups imports, separating standard library from third‑party modules.
* Returns normalized import spans and the list of imported names for clash detection.

### Exceptions (`src/pyonetrue/exceptions.py`)
* Defines custom error types such as `CLIOptionError`, `DuplicateNameError`, and `FlatteningError`.
* Used throughout the pipeline to signal configuration issues or structural problems in the input package.

## Process Flow

1. **CLI Invocation** – The user runs `pyonetrue` with an input package or module and optional flags.
2. **Context Construction** – `cli.main` creates a `FlatteningContext` and resolves which entry points or main modules should be built.
3. **Module Discovery** – The context iterates over `sorted(path.rglob('*.py'))` so builds on every platform discover modules in the same order, forming `FlatteningModule` objects for each path that matches the include/exclude filters.
4. **Span Extraction** – Each module is parsed by `extract_spans`, producing ordered spans that describe imports, definitions, main guards, and other top‑level code.
5. **Main Guard Collection** – Depending on `--all-guards` and `--guards-from`, guard spans are aggregated for inclusion in the final output.
6. **Import Normalization** – All gathered imports are processed by `normalize_imports` to eliminate duplicates and sort them deterministically.
7. **Dependency Ordering** – Modules are topologically sorted based on their import relationships so referenced symbols appear after their definitions. A CLI flag lets users supply a custom order when necessary.
8. **Assembly & Clash Checking** – The context orders docstrings, imports, class/function definitions, logic, guard blocks, and optional `__main__.py` content. Name clashes raise `DuplicateNameError` unless ignored.
9. **Post-build Validation** – The flattened output is compiled with `py_compile` or imported to fail fast if any symbol is undefined.
10. **Output Generation** – The assembled spans are written to stdout or the path specified by `--output`. When multiple entry points are built, files are placed under the given output directory.

## Data Flow

The pipeline converts each source file into a list of `Span` objects. These spans flow through normalization and ordering steps until they become lines in the final flattened module. The design keeps raw source text intact, ensuring that formatting is preserved wherever possible.

## Extensibility

The modular separation between CLI, context management, AST extraction, and import normalization allows additional analysis passes such as plugin-based import handlers. Each component exposes clear responsibilities, keeping the flattening logic independent from command parsing and user interface concerns.

The next release expands this pipeline with rename-aware name deduplication. Import normalization will produce a rename map for any clashing identifiers and apply those renames throughout the AST so modules can be flattened without manual aliasing. Along with this, AST-level conflict resolution rewrites conflicting definitions across modules to maintain unique names in the final output.

## Determinism and Validation (v0.8.0)

Version 0.8.0 incorporates recommendations from the CI failure analysis to guarantee reproducible builds:

* Module discovery always iterates over paths in sorted order.
* Modules are topologically sorted by dependencies, with an optional CLI flag for custom ordering.
* After assembly, the flattened module is compiled or imported to catch undefined symbols early.
* Tests include packages with cross-module references to assert deterministic output across platforms.

## Rationale

Following the guidance in the design document types, this overview explains how **pyonetrue** is structured without delving into API details or test plans. It focuses on the responsibilities and interaction of components so new contributors can understand the intention behind the code layout.
