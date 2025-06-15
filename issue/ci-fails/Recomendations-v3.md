# Handling Symbol Ordering

Flattening merges modules into a single file but does not currently guarantee that
symbols are declared before top-level code uses them. A module containing
`print(foo())` can appear before `foo` is defined, leading to a `NameError` at
runtime.

## Recommendations

1. **Dependency ordering** – Parse each module for imported or referenced names
   and order modules topologically so that any required definitions appear
   earlier in the flattened file.
2. **Preserve module boundaries** – Keep each module's code grouped together and
   optionally insert explicit `import` statements to maintain runtime ordering.
3. **Static validation** – Analyze top-level statements for references to
   undefined names and fail fast if flattening would produce unsafe ordering.
4. **Configurable grouping** – Provide a flag to emit modules sequentially after
   sorting, preserving their original internal ordering without interleaving
   spans from different modules.
