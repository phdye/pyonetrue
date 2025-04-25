# pyonetrue Design Document (Version 0.5.3 — syntax‑only)

## Purpose

`pyonetrue` is a CLI tool that flattens one or more Python modules and packages into a single well-structured output module. It supports top-level span reordering, import normalization, and precise handling of entrypoints, including explicit support for `__main__.py`. **All input modules must parse cleanly.**

Unlike version 0.3.x (monolithic source buffer) and version 0.4.0 (recovery spans and placeholders), version 0.5.3 **requires syntactically correct modules**, enabling a single-path transformation pipeline.

---

## High‑Level Objectives

- ✅ Produce a fully ordered, executable Python module from:
  - a named Python package 
  - an individual `.py` file
  - a directory containing a Python package
- ✅ Normalize and deduplicate imports
- ✅ Preserve relative ordering of classes, functions, and logic
- ✅ Treat `__main__.py` as a special case: **not reordered**, only cleaned and appended
- ✅ Allow user‑directed inclusion of `if __name__ == '__main__'` blocks
- ✅ Compose result from **structured module parts**
- ✅ Detect and error on top‑level name clashes unless explicitly ignored
- ➖ Drop error‑tolerance and recovery mechanisms

## Architectural Overview

Each input module is:
1. Parsed into a list of `CodeSpan` objects.
2. Tagged with its origin (path, module name, or user label).
3. Grouped into structural parts: imports, classes, functions, logic, main guards.

The reordering process happens at the **module level**, then results are merged respecting the global policy:
- Import cleanup across all modules
- `__main__.py` isolated early, cleaned, and appended last (no reordering)
- Selected main guard appended after reordered content
- Duplicate top-level name errors detected unless `--ignore-clashes` is set

Because all modules parse cleanly, there is no fallback parse or invalid span logic: the pipeline always proceeds via standard AST parsing.

---

## CLI Interface

### Usage

```
Usage:
  pyonetrue [options] <input>
  pyonetrue (-h | --help)
  pyonetrue --version

Flatten Python package files into a well ordered, single module.

<input> can be a python package name, a directory or a file:
  package    The <package-root> via PYTHONPATH becomes the directory.
  directory  All Python files under the directory will be flattened.
  file       It will be ordered, fixes a poor ordering.

In all cases, the module is written to the specified output file or stdout.

A main guard is a block of code that is only executed when the module
is run as a script. It is typically used to test the module or to
provide a command-line interface. The main guard is usually
written as:

    if __name__ == '__main__':
        # code to execute when the module is run as a script
        pass

<package>/__main__.py is a special module that is executed when the
package is run as a script.  It is typically used to provide a command-line
interface to the package.  Unless `--no-cli` is specified, if such a module
is present, it will be included after all other modules.  Other
__main__.py modules are not included by default.  If you want to include
one of them instead, you can use the --main-from option to specify the
sub-package from which to include __main__.py.

Default behavior is to :
* All relative imports are eliminated. Flattened output is fully self-contained.
* Main guards are discarded, but this can be changed with the --main-all
  or --main-from options.
* Write the output to stdout, but this can be changed with the --output
* Name clashes, duplicate top-level names, are not allowed by default.

Options:
  --output <file>      Write output to file (default: stdout).
  --no-cli             Do not include package's __main__.py.
  --main-from <mod>    Include __main__.py from the specified sub-package.
                       Only one __main__.py module is allowed.
                       Overrides --no-cli.
  --all-guards         Include all __main__ guards. (default: discard)
  --guards-from <mod>  Include __main__ guards only from <mod>.
  --exclude <exclude>  Exclude specified packages or modules, comma separated.
  --include <include>  Include specified packages or modules, comma separated.
  --ignore-clashes     Allow duplicate top-level names without error.
  -h, --help           Show this help message.
  --version            Show version.
```

---

## CLI Options and Behavior

### `--no-cli`

- Suppresses generation of **synthetic CLI helpers** (auto-injected `main()` functions, docopt parsers).
- **Suppresses primary package's `__main__.py` content** unless explicitly included via `--main-from`.

### `--guards-all`

- Includes **all `if __name__ == '__main__'` blocks** from all `.py` files.

### `--guards-from=<mod1,mod2,...>`

- Includes only specified modules' `if __name__ == '__main__'` blocks.
- Other main guards are omitted.

### `--main-from=<mod1,mod2,...>`

- Includes only the specified modules' `__main__.py` bodies.
- **Suppresses the primary package's `__main__.py`** unless it is explicitly listed.

---

## Main Block and File Handling

| Situation                  | Behavior |
|:----------------------------|:---------|
| No special flags            | Include primary package's `__main__.py` body |
| `--no-cli` alone             | Exclude primary package's `__main__.py` body |
| `--main-from=submod`         | Include only `submod`'s `__main__.py`, suppress primary unless listed |
| `--guards-all`              | Include all `if __name__ == '__main__'` guards from all modules |
| `--guards-from=a,b`         | Include only main guards from modules `a`, `b` |

---

## Processing Pipeline

1. **Input Collection**
   - Resolve paths and modules from CLI.
   - Classify into `.py` files, packages, or virtual inputs.
2. **Module Analysis (per file)**
   - Load source.
   - Extract spans via AST.
   - Tag origin.
3. **Span Classification**
   - Split into imports, classes, functions, orphans, main guards.
4. **Import Normalization**
   - Deduplicate and group imports (stdlib, third-party, local).
5. **Content Assembly**
   1. Normalized imports
   2. Reordered spans (excluding main guards)
   3. Selected main block(s)
   4. Cleaned `__main__.py` (if included)
6. **Top-Level Symbol Collision Detection**
   - Error on duplicates unless `--ignore-clashes`.
7. **Output Rendering**
   - Render spans into final module string.
   - Write to file or stdout.

---

## Future Enhancements

- [ ] Top-level name deduplication with rename hints
- [ ] AST-level merge conflict resolution
- [ ] Cross-module symbol references and inlining
- [ ] Source map / trace output for diagnostics

---

## Version Status

This document specifies version **0.5.3** of `pyonetrue`, which **requires** syntactically correct modules, enabling a simplified, single-path flattening pipeline without recovery layers.
