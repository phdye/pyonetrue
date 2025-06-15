# Recommendations

The CI failure occurs because `pyonetrue` flattens modules in the order returned by `Path.rglob`, which varies between platforms. When the order changes, a symbol can appear before its definition (e.g. `Span` in `extract_ast`). To resolve this:

1. **Sort discovered modules.** Update `FlatteningContext.discover_modules()` to iterate over `sorted(path.rglob('*.py'))`. This guarantees a consistent traversal order and avoids out-of-order declarations.

2. **Perform dependency analysis.** After collecting modules, parse their ASTs and order them so that imported symbols appear after the modules that define them. A simple approach is a topological sort based on `import` relationships.

3. **Add a verification step.** Once the output file is generated, run `python -m py_compile` or import the module to ensure no `NameError` occurs due to missing symbols.

4. **Expand tests.** Add unit tests that flatten a package with cross-module references to confirm the build is deterministic and that symbols are declared before use.
