# 🛠️ `pyonetrue` Developer Guide

Version: **0.5.3**
Status: **Stable, Syntax-only Pipeline**

---

## 🌟 Goals

* Deterministic output from unordered/multi-module input
* Modular parsing and transformation pipeline
* Complete control over CLI entrypoint inclusion
* No fallbacks, no guesswork — only parseable, correct code

---

## 🚀 Core Pipeline

1. **Input Resolution**

   * Accepts file/module/package
   * Resolves all `.py` sources from target

2. **Module Parsing**

   * Uses `ast.parse()`
   * Converts to internal `CodeSpan` format

3. **Span Classification**

   * Categorize each span as:

     * `Import`, `Class`, `Function`, `Logic`, `MainGuard`

4. **Normalization**

   * Imports deduplicated and sorted
   * Relative imports rewritten/eliminated

5. **Main Block Handling**

   * `if __name__ == '__main__'`: conditional inclusion
   * `__main__.py`: preserved and appended, optionally suppressed

6. **Name Collision Detection**

   * Top-level function/class clashes raise error unless `--ignore-clashes`

7. **Output Generation**

   * Renders `CodeSpan` objects to flat source buffer
   * Written to file or stdout

---

## 📊 Output Span Ordering

Order is always:

1. Normalized Imports (stdlib, 3rd party, local)
2. Classes
3. Functions
4. Top-level logic
5. `if __name__ == '__main__'` (if selected)
6. `__main__.py` body (if selected)

---

## 🤷 Internals

### `CodeSpan`

* Captures logical code unit with metadata:

  * type: `Import`, `Class`, `Function`, `Guard`, etc
  * origin: source path or module
  * start/stop lines

### `SpanClassifier`

* Walks AST, produces typed spans from each file

### `ModuleRenderer`

* Emits final ordered text buffer

---

## 🔍 CLI Details Recap

| Flag                | Meaning                                |
| ------------------- | -------------------------------------- |
| `--no-cli`          | Skip `__main__.py`                     |
| `--main-from x`     | Include only `x/__main__.py`           |
| `--guards-from x,y` | Include main guards from `x`, `y` only |
| `--all-guards`      | Include all guards                     |
| `--ignore-clashes`  | Suppress duplicate name check          |

---

## 🛡️ Error Policies

| Error            | Condition                              |
| ---------------- | -------------------------------------- |
| `SyntaxError`    | Any module fails to parse              |
| `NameClashError` | Duplicate top-level name across inputs |

---

## 🔄 Sample Invocation

```bash
pyonetrue --output flat.py --main-from mypkg.cli src/mypkg
```

* Flattens and reorders all `src/mypkg/**/*.py`
* Appends `cli/__main__.py`
* Ensures final module is fully import-clean

---

## 🌐 Package Composition: Structural Facets

For tooling like `pyonetrue`, the following elements define a complete Python package:

* `__init__.py`: defines importable namespace, initializes globals
* `__main__.py`: entrypoint when `python -m package` is invoked
* `setup.py` / `pyproject.toml`: (ignored by `pyonetrue`, packaging only)
* Classes: business logic, behaviors
* Functions: reusable operations
* Top-level logic: constants, config, side-effects
* Guards: `if __name__ == '__main__'`, optional CLI
* Imports: grouped stdlib → third-party → internal
* Metadata: version, author, CLI args (e.g. `--help`)

Optional but common:

* CLI `main()` function
* docopt/argparse parser
* logging / diagnostics

---

## 🚫 Exclusions

* No syntax fallback or placeholder logic
* No import execution or module import resolution
* No side-effect analysis — source-only

---

## 📊 Future Enhancements

* Rename-aware name deduplication
* AST-level conflict resolution
* Source map and debug annotations
* Cross-module function inlining
* Flattening metrics / diagnostics

---

## 🎯 Summary

`pyonetrue` is a declarative, deterministic flattening tool. It uses strict parsing, AST-backed span classification, and output normalization to generate clean, single-module Python source files. It is ideal for reproducible CLI builds, packaging simplification, and toolchain integration.
