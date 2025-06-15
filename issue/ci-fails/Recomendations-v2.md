# Ordering Recommendations

The CI failure showed that symbols might be used before they are defined when `pyonetrue` flattens packages.  The root cause is that module order depends on how files are discovered.

## Proposed Fixes

- **Sort discovered modules**
  - Iterate over `sorted(path.rglob('*.py'))` to get a consistent baseline order.
- **Analyze import dependencies**
  - Build a dependency graph from `import` statements and topologically sort modules so that imported code appears first.
- **Two-pass flattening**
  - In the first pass, parse modules and record global definitions.  In the second pass, emit modules in an order that satisfies dependencies.
- **Allow explicit ordering**
  - Provide a CLI option to accept a user-specified module list when automatic ordering is insufficient.