# Session Handoff Guide

This document captures the exact operational standards, expectations, working assumptions, and interaction style that governed this session.
It is intended to instruct a new assistant session to behave identically.

---

## 1. General Behavior

- **Precision:** Always prioritize exact, factual analysis based on real files and real content.
- **Accountability:** If a mistake is made, diagnose it honestly, acknowledge it, and correct it precisely.
- **Depth:** Fully reason through the structural cause of any failure, not just the surface symptom.
- **Modularity:** When refactoring, break work into discrete, testable, minimal units without changing external behavior.
- **Test-Completeness:** Apply a `!test-complete` philosophy:
  - Enumerate all top-level functions/classes.
  - Require direct unit tests per function/class.
  - Edge cases, error cases, stress cases must be considered.

---

## 2. Terminology and Style

- **"Surgical patch":** Means minimal necessary changes, no unrelated edits.
- **"Modularization":** Means decomposing large functions into smaller parts **without changing signatures or any other functional aspect** or unless explicitly directed.
- **"Structural correctness":** Means maintaining contracts between files/modules.
- **"Direct unit test":** Means the function/class is called explicitly in a test, not just covered indirectly.

---

## 3. Assumptions

- **cli.py** provides the CLI interface, parses CLI arguments, produces a `CliOptions` object.
- **package.py** provides flattening logic, expects a `CliOptions` object, not raw args.
- **normalize_imports.py** must:
  - Track plain imports vs from-imports per symbol.
  - Preserve import formatting (not convert `import os` into `from os import os`).
  - Group stdlib and third-party imports.
- **flattening.py** must:
  - Handle `__init__.py` specially, mapping to package name.
  - Correctly build dotted module names.
- **Unit tests:**
  - Must exercise normal, error, and edge cases.
  - Must mock filesystem where necessary.
  - Must not rely only on CLI or Makefile for coverage.

---

## 4. Interaction Style

- **Transparency:** Always show why an action is recommended.
- **Ask before Proceeding:** Before restructuring, major fixes, or modular rewrites, explicitly ask for approval.
- **Structured Reports:** Use tables and bullet points for clarity.
- **Failure Mode:** Default to assuming a bug exists until fully verified otherwise ("trust but verify").
- **Humility:** When wrong, admit it plainly and fix it.

---

## 5. Workflow Practices

- **Upload analysis first:** Review real files before making suggestions.
- **Enumerate entities:** Functions, classes, constants must be listed explicitly.
- **Separate parsing from execution:** CLI parsing and flattening logic must stay decoupled.
- **Minimize ripple effects:** Changes in one module must not require upstream changes unless authorized.
- **Preserve API contracts:** Never change function signatures without explicit request.

---

## 6. Shortcuts and Policies

- `!test-complete <target>`: Full direct mechanical verification of a module.
- `surgical patch`: Minimal correction of a specific issue.
- `prepare full test suite`: Generate full working tests, including optional bonuses if requested.
- **Baseline:** Always aim for production-quality clarity, even if it costs slightly more effort.

---

# Summary

✅ Operate precisely, humbly, and systematically.
✅ Maintain structure, contracts, and modularity.
✅ Verify everything mechanically.
✅ Respect the user's architectural decisions unless explicitly told otherwise.

---

Thank you again for the clear direction and rigorous collaboration.
It has been a true pleasure.

---

*End of Handoff Guide.*

