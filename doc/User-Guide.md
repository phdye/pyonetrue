# 📘 `pyonetrue` User Guide

Version: **0.5.3**
Status: **Stable, syntax-only**

---

## 🚜 Quick Start

Flatten a package into a single module with CLI:

```bash
pyonetrue --output foobar.py foobar
```

Flatten a package into a single module, without CLI:

```bash
pyonetrue --no-cli --output foobar.py foobar
```

Flatten a package directory into a single module:

```bash
pyonetrue --output foobar.py src/foobar/
```

Flatten a single Python file:

```bash
pyonetrue pre-flattened.py --output ordered.py
```

Include alternate CLI entrypoint:

```bash
pyonetrue src/foobar/ --main-from foobar.altcli --output altcli.py
```

---

## 📆 Accepted Input Forms

`pyonetrue` accepts:

* A **Python package** (e.g. `src/mypkg`)
* A **directory** containing `.py` files
* A single **Python module** (e.g. `myfile.py`)

Output is written to `stdout` or `--output` path.

---

## 🏠 Flattened Output Behavior

* All **relative imports** are rewritten or eliminated
* Duplicate imports are **deduplicated and grouped**
* Top-level contents are **reordered deterministically**
* `__main__.py` and `if __name__ == '__main__'` blocks are handled by user flags

---

## 🔢 CLI Options

| Option                | Description                                    |
| --------------------- | ---------------------------------------------- |
| `--output <file>`     | Write to specified file (default: stdout)      |
| `--no-cli`            | Exclude package's `__main__.py`                |
| `--main-from <mod>`   | Include only this module's `__main__.py`       |
| `--all-guards`        | Include all `if __name__ == '__main__'` blocks |
| `--guards-from <mod>` | Include guards only from these modules         |
| `--exclude <mods>`    | Comma-separated modules/packages to exclude    |
| `--include <mods>`    | Modules/packages to force include              |
| `--ignore-clashes`    | Allow duplicate top-level names                |
| `--help`, `--version` | Show help/version                              |

---

## 🔥 CLI & Guard Behavior

| Situation           | Behavior                                        |
| ------------------- | ----------------------------------------------- |
| Default             | Primary `__main__.py` is appended               |
| `--no-cli`          | `__main__.py` is excluded                       |
| `--main-from x`     | Only `x/__main__.py` is included                |
| `--all-guards`      | Includes all `if __name__ == '__main__'` blocks |
| `--guards-from x,y` | Only from `x`, `y`                              |

---

## 🚧 Duplicate Symbol Detection

By default, `pyonetrue` checks for duplicate top-level function/class names, imported symbols across files.

Use `--ignore-clashes` to disable this.

---

## 📄 Output Structure

Flattened output always emits spans in this order:

1. Imports (stdlib, 3rd-party, local)
2. Classes
3. Functions
4. Top-level statements (e.g. `x = 3`)
5. `if __name__ == '__main__'`
6. `__main__.py` body (if included)

---

## 🧠 Testing Advice

Set `PYTHONPATH=src` to test the flattened module:

```bash
PYTHONPATH=src pytest tests
```

For subprocess isolation:

```python
import subprocess
subprocess.run(["pytest", "tests"], env={"PYTHONPATH": "src"})
```

---

## 🙋 FAQ

**Q: Why was my CLI not included?**
A: Use `--main-from your.module` to specify it. Default only includes package-level `__main__.py`.

**Q: I got a duplicate name error!**
A: Either rename in source, or live dangerously and use `--ignore-clashes`.

**Q: Does this replace setuptools?**
A: No — it's a source-flattening tool, not a packaging tool.

---

## 🔗 Related Files

* `Design.md`: Pipeline & architectural design
