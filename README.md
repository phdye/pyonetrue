# pyonetrue

**pyonetrue** is a CLI tool for flattening Python packages into a single-file module, carefully preserving imports, top-level order, and optional entry points. 

It supports:
- Inclusion or exclusion of specific modules
- Optional retention of `if __name__ == '__main__'` guards
- Controlled selection of `__main__.py` entrypoints
- Collision detection for top-level functions and classes

This tool is designed for developers who need controlled flattening for deployment, archiving, or lightweight distribution scenarios.

See [USAGE.txt](./doc/0.5/USAGE.txt) for full command-line documentation.
