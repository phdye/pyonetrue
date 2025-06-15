# CLI Specification for `pyonetrue`

This document describes the command line interface for **pyonetrue**. It defines
available options, argument formats and the expected behaviour of the tool.
The goal is to provide a precise contract so that users and developers know
exactly how to invoke the program and what results to expect.

## Command Synopsis

```
pyonetrue [options] <input>
pyonetrue (-h | --help)
pyonetrue --version
```

`<input>` may be a Python package name, a directory or a single module. The
source is flattened into a self‑contained module and written to the output path
or to `stdout`.

### Input Forms

* **Package name** – resolved using `PYTHONPATH`.  All modules in the package
  are flattened.
* **Directory** – every `*.py` file under the directory is processed.
* **Single file** – only the given module is flattened.

## Options

| Short / Long flag      | Description                                                         |
|-----------------------|---------------------------------------------------------------------|
| `-s`, `--shebang <s>` | Prepend `<s>` when `__main__.py` is appended (default: `#!/usr/bin/env python3`). |
| `-o`, `--output <f>`  | Write output to `<f>` instead of `stdout`.                           |
| `-M`, `--module-only` | Build a module without any CLI entry point.  No `__main__.py` and no `if __name__ == '__main__'` guards are included. |
| `--entry <mod:func>`  | Build specifically for the given entry point.  May be repeated.  If omitted, all entry points defined in `pyproject.toml` are used. |
| `-m`, `--main-from <mod>` | Include `__main__.py` from the specified sub-package.  Mutually exclusive with `--module-only`. |
| `-a`, `--all-guards`  | Include all `if __name__ == '__main__'` blocks.  By default they are discarded. |
| `-g`, `--guards-from <mod>` | Include main guards only from `<mod>` (comma separated if multiple). |
| `-E`, `--exclude <mod>` | Exclude the given modules or packages (comma separated). |
| `-i`, `--include <mod>` | Include specific modules inside excluded trees (comma separated).  Requires `--exclude`. |
| `--ignore-clashes`    | Allow duplicate top-level names without raising `DuplicateNameError`. |
| `--show-cli-args`     | Print the parsed arguments for debugging and exit.                   |
| `-h`, `--help`        | Show usage information and exit.                                    |
| `--version`           | Show version information and exit.                                  |

### Option Semantics

* `--include` can only be used in conjunction with `--exclude`.  The included
  modules must be located under one of the excluded modules.
* When multiple entry points are specified with `--entry`, the `--output`
  argument must point to a directory.  One output file per entry is written
  inside that directory using the entry name as the file stem.
* `--module-only` cannot be combined with `--main-from` or `--entry`.

## Behaviour

1. All relative imports are rewritten so the flattened output is fully
   self‑contained.
2. Imports are normalised and grouped by origin (stdlib, third party, local).
3. Modules are ordered deterministically: imports, classes, functions,
   top‑level statements, optional guards, optional `__main__.py`.
4. If duplicate top‑level names are detected, the program exits with an error
   unless `--ignore-clashes` is specified.
5. When `--show-cli-args` is used, the parsed configuration is printed and the
   program exits immediately with status `0`.

### Exit Codes

* `0` – success.
* `1` – any error during argument parsing or flattening.

The tool does not currently differentiate error types via specific codes.

## Example Invocations

Flatten a package and write the result to a file:

```bash
pyonetrue src/mypkg --output flat/mypkg.py
```

Flatten without including any command line entry point:

```bash
pyonetrue --module-only src/mypkg --output flat/mypkg.py
```

Include a custom `__main__.py` from a subpackage:

```bash
pyonetrue --main-from mypkg.cli src/mypkg --output cli_ready.py
```

Selectively include a module inside an excluded tree:

```bash
pyonetrue --exclude .tests --include .tests.helpers src/mypkg --output clean.py
```

## Output Guarantees

The generated module is valid Python 3.10+ source.  Line ordering and import
normalisation are deterministic so repeated runs with the same inputs produce
identical output.

