# Handling Multiple Entry Points

The **`pyonetrue`** tool currently focuses on flattening a package into a single
module and optionally appending the package's `__main__.py` or individual
`if __name__ == '__main__'` blocks.  Packages such as `logtool` and `dlocate`
(available as submodules under `issue/multiple-entrypoints/`) expose *multiple*
console entry points.  Each entry point usually maps to a `main()` function in a
module.

This note explores how `pyonetrue` could support such layouts and other common
styles.

---

## Proposed Approach

1. **Accept an explicit entry point name**
   - Introduce a CLI option like `--entry <mod[:func]>`.
   - `mod` is the dotted module path.  `func` defaults to `main` if omitted.
   - Example: `pyonetrue --entry logtool.cli:main logtool`.

2. **Resolve the entry module**
   - Treat `mod` just like other modules in the package.  Flatten all modules
     required by the package, then place the specified function body (or a call
     to it) at the bottom of the output module.

3. **Generate a runnable script**
   - Append a `if __name__ == '__main__'` block that calls `func()`.
   - Optionally prepend a shebang when writing to a file.

4. **Support multiple names**
   - Allow specifying several `--entry` options to emit multiple single-file
     scripts in one invocation, or run the command separately for each entry
     point.

---

## Other Entry Point Styles

Besides a conventional `main()` function, real-world projects use a few common
patterns:

- **Module-level `main`**: `python -m pkg.module` executes `pkg/module.py`.
  Already supported via `--main-from pkg.module`.
- **Click/Argparse wrapper**: a function like `cli()` or `app()` is exported and
  used in `entry_points.console_scripts`.  Our `--entry` option should allow
  specifying any function name.
- **Class-based CLI**: an object with `__call__()` is invoked from the entry
  point.  Treat it the same as a function target.
- **Standalone scripts in `bin/`**: sometimes a small script imports the package
  and calls into it.  These can be flattened by specifying the script path as
  `<input>` directly.

Supporting these patterns keeps the interface flexible while remaining explicit.

---

## Recommendation

Implementing a `--entry` option (and its plural form) would let `pyonetrue`
produce single-file programs for each console entry point.  The tool remains
explicit and deterministic: users state exactly which function represents the
CLI.  Packages with multiple scripts (like `logtool` or `dlocate`) can then be
flattened one entry at a time without any special casing.
