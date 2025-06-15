# 🧩 Writing `pyonetrue`: A Story of Flattening, Failing, and Finally Flying

> **"When modular code meets monolithic needs."**

Welcome to the tale of **`pyonetrue`** — a deceptively simple command-line tool designed to do something Python itself never promised: convert entire packages, with multiple modules, CLI entry points, import quirks, and main guards, into **a single, deterministic `.py` file**.

## 🌱 The Problem That Wouldn’t Stay Small

It started with a need. Not a dream, not a grand vision. Just a small need:

> *"I want to send someone my CLI project as a single file. No `setup.py`, no `requirements.txt`, no weird zip import hack. Just a `.py` file that works."*

So you start manually copy-pasting `core.py`, `utils.py`, `cli/__main__.py`... and immediately hit problems:

* Relative imports like `from .foo import bar` break.
* `__main__.py` has no context.
* `if __name__ == '__main__'` guards are scattered.
* Duplicate function names slip in and overwrite each other silently.

So begins the descent into flattening hell.

---

## 🔧 Building the First Prototype (v0.3.x)

The earliest version of `pyonetrue` worked like a naive bundler:

* Read each `.py` file as a text buffer.
* Yank out function/class definitions using regex.
* Discard anything that failed to match.
* Smush it all together in one big `output.py` file.

Did it run? Sometimes.
Did it work? Occasionally.
Did it fail silently and confusingly? Absolutely.

We realized: **flattening isn’t text merging. It’s structure preservation.**

So we tore it all down.

---

## 🧠 Version 0.4: The Era of Span Recovery

In version 0.4, we introduced a more principled model:

* Parse each file into an AST.
* Identify known structures (`ClassDef`, `FunctionDef`, `Import`, etc).
* Tag each with a `CodeSpan` that tracked origin, type, and boundaries.
* Recover lines from source using lineno ranges.
* Rebuild based on these spans.

This got us 80% of the way — and introduced the key idea that still defines `pyonetrue` today:

> *"You don’t flatten files. You extract structure, and reassemble a program."*

But... version 0.4 still tried to be nice. It would skip invalid code. It would let multiple functions of the same name exist in peace. It would *forgive*.

Forgiveness, it turns out, is not a virtue in deterministic flattening.

---

## 💎 Version 0.5: Clean or Die

Version 0.5 introduced the **AST-or-nothing pipeline**.

No more recovery. No more skipping broken files. No more partial output.

* All modules must parse.
* All names must be unique.
* All inputs are tagged and ordered.

Every file is analyzed as a set of `CodeSpan` objects:

* Imports (deduplicated and grouped)
* Classes
* Functions
* Top-level logic (rare but real)
* `if __name__ == '__main__'` guards
* `__main__.py` body

You choose your flattening behavior:

* Want the CLI included? Use `--main-from foo.cli`.
* Want every `__main__` guard? Use `--all-guards`.
* Want a pure library? Use `--module-only`.

The philosophy became clear:

> *"No guessing. No heuristics. Just valid structure in, valid structure out."*

---

## ⚙️ The CLI That Stayed Honest

The CLI interface is brutally explicit:

```bash
pyonetrue --output flat.py src/mytoolkit --main-from mytoolkit.cli
```

This means:

* Flatten `src/mytoolkit/**/*.py`
* Append only `cli/__main__.py`
* Deduplicate imports
* Reorder all top-level spans

And that’s it. No magic.

If you do something weird — like duplicate a top-level function — it errors. Unless you opt-in to chaos with `--ignore-clashes`.

---

## 🧪 The Tests That Keep Us Honest

Because `pyonetrue` modifies *code*, not *behavior*, our tests must:

* Parse all modules with `ast.parse()`
* Assert top-level name uniqueness
* Confirm CLI inclusion logic works as expected
* Check flattened output for import order and guard inclusion

We also added structural end-to-end tests: flatten `src/pyonetrue`, then test that it:

* Still passes the complete test suite.
* Has no unresolved imports.
* Finally, this was incorporated as a test in the test suite named round trip.

---

## 🔭 What’s Next?

Flattening is just the beginning. We’re exploring:

* AST-level name deduplication (with rename maps)
* Source maps (trace spans to origin file)
* Import rewriter plugins (custom import handling)
* Tooling for interactive conflict resolution

---

## ❤️ Why It Matters

Flattening isn’t a gimmick. It’s a statement:

> *"Your source code should be reproducible. Your CLI should be explainable. Your tooling should respect your structure."*

In a world of zip imports, magic runners, and `setup.cfg` sorcery, `pyonetrue` is one small act of clarity.

No smoke. No mirrors.
Just code.

---

## 🙏 Credits

* Built by Spirits of Change
* Powered by Python’s AST, and our refusal to write a bundler

---

> *pyonetrue: Because your code deserves to be read.*
