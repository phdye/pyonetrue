# Recommendations for Ensuring Declaration Order

The flattening process does not guarantee that symbols appear before use. This can break imports in the flattened module. Here are some possible approaches to correct the issue:

- **Topological sort the modules.** Analyze import statements to build a dependency graph among modules in the package. Emit modules in dependency order so that each definition precedes its dependents.
- **Resolve dependencies within each module.** Parse the AST of individual modules to determine symbol dependencies (classes, functions). Reorder statements so that all names are defined before usage.
- **Introduce explicit module initialization logic.** Instead of relying on declaration order, wrap each module in a function or class and invoke them in the correct order during runtime.
- **Consider using existing packaging tools.** Tools like `setuptools` or `importlib` already handle dependencies; the flattening script might leverage them instead of manual processing.

Choosing among these approaches depends on how deeply `pyonetrue` should understand the code it flattens.