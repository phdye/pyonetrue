# 🧰 pyonetrue

**`pyonetrue`** is a command-line tool that flattens one or more Python modules or packages into a single, well-ordered, standalone `.py` file. It is designed for scenarios where clean, portable, and deterministic source output is essential—such as deployment, or producing a minimized entrypoint for CLI tools.

---

## ✨ Key Features

- 🔁 **Reorders and normalizes** imports, classes, functions, and logic blocks
- 🔍 **Eliminates relative imports**, making the output fully self-contained
- 🧠 **AST-backed parsing** ensures only syntactically valid code is accepted
- 🛑 **Detects name collisions** between top-level functions and classes
- 🔌 **Customizable CLI inclusion** via main guards and `__main__.py` policies
- 🗂️ **Supports packages, directories, or single modules** as input

---

## 📦 Example Usage

Flatten a Python package:

```bash
pyonetrue src/mypkg --output flat/mypkg.py
```

Flatten a single module:

```bash
pyonetrue src/mypkg/utils.py --output flat/utils_flat.py
```

Include CLI logic from `mypkg.cli.__main__.py`:

```bash
pyonetrue --main-from mypkg.cli src/mypkg --output cli_ready.py
```

Include all `if __name__ == '__main__'` blocks from all modules:

```bash
pyonetrue --all-guards src/mypkg --output with_guards.py
```

---

## 🧪 Valid Input Types

`<input>` may be:

* A **Python package** directory (`src/mypkg`)
* A general **directory** containing Python modules
* A **single `.py` file**

All files must be **syntactically valid Python 3.10+**. Any parse error will halt the flattening pipeline.

---

## 🛠️ CLI Flags (Quick Reference)

| Option                | Description                                    |
| --------------------- | ---------------------------------------------- |
| `--output <file>`     | Write output to this file (default: stdout)    |
| `--module-only`       | Build without any `__main__.py` or CLI         |
| `--main-from <mod>`   | Include only `mod.__main__.py`                 |
| `--entry <entry>`     | Build specifically for the given entry point   |
| `--all-guards`        | Include all `if __name__ == '__main__'` blocks |
| `--guards-from <mod>` | Include only guards from given modules         |
| `--exclude <mods>`    | Omit these modules (comma-separated)           |
| `--include <mods>`    | Explicitly include additional modules          |
| `--ignore-clashes`    | Allow duplicate top-level names                |

See [`USAGE.txt`](./doc/USAGE.txt) for a full CLI specification.

---

## ⚙️ Processing Pipeline

1. **Resolve and load source files** (from file, package, or directory)
2. **Parse each file** into AST and extract `CodeSpan` units
3. **Classify** spans as imports, classes, functions, logic, or main guards
4. **Normalize** imports and top-level structure
5. **Detect duplicate names** unless `--ignore-clashes` is used
6. **Emit output** to a clean single `.py` file or stdout

---

## 📚 Flattening Strategy

The flattened output is ordered as follows:

1. **Imports** (stdlib → third-party → local)
2. **Classes**
3. **Functions**
4. **Top-level logic** (e.g., assignments, print statements)
5. `if __name__ == '__main__'` blocks (optional)
6. `__main__.py` contents (optional)

---

## 🔐 Limitations

* ❌ No support for invalid syntax, recovery modes, or partial parsing
* ❌ Does not interpret or run modules—it is **source-only**
* ❌ Does not build wheels or packages—flattening only

See also [`doc/Bundling-Challenges.md`](./doc/Bundling-Challenges.md)

---

## 🧰 Integration

This tool is used internally by:

* Custom CI pipelines where deterministic `.py` output is needed
* Testing frameworks requiring import-clean builds

---

## 🌍 Design Reference

For implementation architecture and future roadmap, see:

* [`doc/Design.md`](./doc/Design.md)
* [`doc/Developer-Guide.md`](./doc/Developer-Guide.md)
* [`doc/User-Guide.md`](./doc/User-Guide.md)
* [`doc/Bundling-Challenges.md`](./doc/Bundling-Challenges.md)

---

## 📜 License

Non-Commercial Use Only - see `LICENSE` file.

---

## 👥 Author

* Philip Dye
