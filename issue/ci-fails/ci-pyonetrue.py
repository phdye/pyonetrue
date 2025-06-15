#!/usr/bin/env python3
"""
Custom exceptions for pyonetrue, each representing a single, specific error scenario.
"""

import ast
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from errno import EEXIST, EINVAL, ENOENT
import functools
import importlib.util
import os
import re
import sys
import time
from typing import List, Tuple, Union

import fnmatch
import io
import ntpath
from operator import attrgetter
import posixpath
from stat import S_ISBLK, S_ISCHR, S_ISDIR, S_ISFIFO, S_ISLNK, S_ISREG, S_ISSOCK


"""
pyonetrue: Flatten Python packages into a well-ordered single module.

Provides CLI entry point and core flattening functionality under the pyonetrue namespace.
"""

__all__ = [
# cli
    "__version__",
    "main",
# extract_ast
    "extract_spans",
    "Span",
# flattening
    "FlatteningContext",
    "FlatteningModule",
    "normalize_a_module_name",
    "normalize_module_names",
# normailize_imports :
    "normalize_imports",
    "format_plain_import",
    "format_from_import",
    "is_stdlib_module",
    "set_line_length",
    "get_line_length",
    "ImportEntry",
# exceptions
    "PyonetrueError",
    "CLIOptionError",
    "DuplicateNameError",
    "ImportNormalizationError",
    "IncludeExcludeError",
    "FlatteningError",
    "ModuleInferenceError",
    "PathError",
]
"""
Custom exceptions for pyonetrue, each representing a single, specific error scenario.
"""

class PyonetrueError(Exception):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Base exception for all pyonetrue errors."""
    pass

class CLIOptionError(PyonetrueError):
    """Raised when invalid or incompatible command-line options are provided to the CLI.

    Use this exception to signal errors such as specifying mutually exclusive flags
    (e.g., `--module-only` and `--main-from`).
    """
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Invalid combination or value of CLI options."""
    pass

class DuplicateNameError(PyonetrueError):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Detected duplicate top-level symbol names."""
    pass

class ImportNormalizationError(PyonetrueError):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Errors during import deduplication and normalization processes."""
    pass

class IncludeExcludeError(PyonetrueError):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Invalid usage of include/exclude flags."""
    pass

class FlatteningError(PyonetrueError):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """General errors occurring in the flattening pipeline."""
    pass

class ModuleInferenceError(PyonetrueError):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Cannot infer package or module name from the given path."""
    pass

class PathError(PyonetrueError):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Errors related to filesystem paths or module resolution."""
    pass
try :
    from pathlib import Path
except ImportError:
    from .vendor.pathlib import Path

DEBUG = False

@dataclass
class FlatteningContext:

    package_path       : Union[Path, str]
    package_name       : str                           = ""
    main_py            : tuple[str, List[Span]]        = (None, [])
    module_spans       : List[tuple[str, List[Span]]]  = field(default_factory=list)
    guard_sources      : dict[str, List[Span]]         = field(default_factory=dict)

    # Discovery -- inclusion/exclusion
    module_only             : bool                          = False
    main_from          : List[str]                     = field(default_factory=list)
    exclude            : List[str]                     = field(default_factory=list)
    include            : List[str]                     = field(default_factory=list)

    # Conflict detection
    ignore_clashes     : bool                          = False

    # Output generation
    output             : str                           = "stdout"
    shebang            : str                           = "#!/usr/bin/env python3"
    guards_all         : bool                          = False
    guards_from        : List[str]                     = field(default_factory=list)
    entry_points       : List[str]                     = field(default_factory=list)

    def __post_init__(self):
        if not self.package_path:
            raise PathError("package_path cannot be empty")
        # Resolve package_path to file, dir, or package name
        path = Path(self.package_path)
        if DEBUG: print(f"DEBUG: Resolved path = {path}", file=sys.stderr)
        if path.exists():
            if path.is_dir():
                self.package_name = path.name
            elif path.is_file():
                self.package_name = path.stem
            else:
                raise PathError(f"input path '{self.package_path}' is not a file or directory")
        else:
            if DEBUG: print("DEBUG: package_path not found as file/dir, trying as package name", file=sys.stderr)
            spec = importlib.util.find_spec(self.package_path)
            if spec and spec.submodule_search_locations:
                path = Path(spec.submodule_search_locations[0])
                self.package_name = path.name
            else:
                raise ModuleInferenceError(f"cannot infer package name from '{self.package_path!r}'")

        self.package_path = path

        if DEBUG: print(f"DEBUG: package_path = {self.package_path}", file=sys.stderr)
        if DEBUG: print(f"DEBUG: package_name = {self.package_name}", file=sys.stderr)

        # Normalize excludes/includes lists to fully-qualified names (if provided)
        if self.exclude:
            if isinstance(self.exclude, str):
                self.exclude = self.exclude.split(",")
            self.exclude = normalize_module_names(self.package_name, self.exclude)
            if self.include:
                if isinstance(self.include, str):
                    self.include = self.include.split(",")
                self.include = normalize_module_names(self.package_name, self.include)
            else:
                self.include = []
            if DEBUG: print(f"DEBUG: exclude = {self.exclude}", file=sys.stderr)
            if DEBUG: print(f"DEBUG: include = {self.include}", file=sys.stderr)
        elif self.include:
            raise IncludeExcludeError("`include` flag require `exclude` to be set")

        # Normalize self.guards_from to fully-qualified names
        if self.guards_from:
            if isinstance(self.guards_from, str):
                self.guards_from = self.guards_from.split(",")
            self.guards_from = [ normalize_a_module_name(mod, self.package_name) 
                                 for mod in self.guards_from ]

    def new_module(self, path: Path) -> "FlatteningModule":
        return FlatteningModule(self, path)

    def add_module(self, obj: Union[str, Path, "FlatteningModule"]) -> None:
        if not obj:
            raise PathError("module path cannot be empty")
        if isinstance(obj, FlatteningModule):
            fm = obj
        elif isinstance(obj, (Path, str)):
            fm = FlatteningModule(self, Path(obj))
        else:
            raise PathError(f"Invalid module path: {obj} -- must be str, Path, or FlatteningModule")

        if DEBUG: print(f"\nDEBUG: Adding module {fm.module = } from {fm.path = }", file=sys.stderr)

        try:
            spans = extract_spans(fm.path)
        except Exception as e:
            raise FlatteningError(f"failed to extract spans from {fm.path}") from e
        if DEBUG: print("DEBUG add_module : spans :\n"+"\n".join(span.text for span in spans), file=sys.stderr)
        self.module_spans.append((fm.module, spans))

        for span in spans:
            if span.kind == 'main_guard':
                self.guard_sources.setdefault(fm.module, []).append(span)

        if fm.module.endswith("__main__"):
            self.main_py = (fm.module, spans)
            if DEBUG: print("DEBUG add_module : main spans :\n"+"\n".join(span.text for span in spans), file=sys.stderr)

    def discover_modules(self) -> None:

        if self.package_path.is_file():
            self.add_module(self.package_path)
            return

        path = Path(self.package_path)

        if path.is_file():
            self.add_module(path)
            return

        if DEBUG: print(f"\nDEBUG: Discovering modules in {self.package_path = }", file=sys.stderr)

        # Determine exactly which __main__.py (if any) we are allowed to accept
        if self.module_only:
            allowed_main = None
        elif self.main_from:
            allowed_main = normalize_a_module_name(self.main_from, self.package_name)
            if not allowed_main.endswith(".__main__"):
                allowed_main = allowed_main + ".__main__"
        else:
            allowed_main = self.package_name + ".__main__"

        if DEBUG: print(f"DEBUG: Discover - {allowed_main = }", file=sys.stderr)

        for subpath in path.rglob('*.py'):
            relpath = subpath.relative_to(path)
            dotted = str(relpath.with_suffix('')).replace('/', '.').replace('\\', '.')
            if dotted.endswith(".__init__"):
                dotted = dotted.rsplit(".", 1)[0]

            full_mod = normalize_a_module_name(dotted, self.package_name)

            if self.exclude and dotted_member_of(full_mod, self.exclude):
                if not (self.include and dotted_member_of(full_mod, self.include)):
                    if DEBUG: print(f"DEBUG: Discover - excluded - skipping module {full_mod = }, from {subpath = }", file=sys.stderr)
                    continue

            if full_mod.endswith(".__main__"):
                if allowed_main is None:
                    if DEBUG: print(f"DEBUG: Discover - no cli - skipping module {full_mod = }, from {subpath = }", file=sys.stderr)
                    continue  # module_only active, skip all __main__.py
                if allowed_main and full_mod != allowed_main:
                    if DEBUG: print(f"DEBUG: Discover - wrong cli - skipping module {full_mod = }, from {subpath = }", file=sys.stderr)
                    continue  # only allow exactly the requested __main__.py
                self.main_py = full_mod

            self.add_module(subpath)

    def gather_root_spans(self):
        docstring = None
        retained_all = None
        retained_imports = []
        retained_logic = []

        for mod, spans in self.module_spans:
            first_logic = True
            for s in spans:
                if docstring is None and first_logic and s.kind == "logic" and (
                    s.text.lstrip().startswith("\"\"\"") or s.text.lstrip().startswith("'''")
                ):
                    docstring = s
                    first_logic = False
                    continue
                first_logic = False

                if mod == self.package_name:
                    if s.kind == "__all__":
                        retained_all = s
                    elif s.kind == "import":
                        retained_imports.append(s)
                    elif s.kind == "main_guard":
                        pass
                    else:
                        retained_logic.append(s)
        return docstring, retained_all, retained_imports, retained_logic

    def gather_module_spans(self):
        non_root_spans = []

        main_mod, _ = self.main_py

        for mod, spans in self.module_spans:
            if mod == self.package_name or mod == main_mod:
                continue
            for s in spans:
                if s.kind != "main_guard":
                    non_root_spans.append(s)

        return non_root_spans

    def gather_main_guard_spans(self):
        result = []
        if self.guards_all:
            for spans in self.guard_sources.values():
                result.extend(spans)
        elif self.guards_from:
            for mod in self.guards_from:
                if mod in self.guard_sources:
                    result.extend(self.guard_sources[mod])
        return result

    def get_main_spans(self):
        main_mod, main_spans = self.main_py
        if not (main_mod and main_spans and not self.module_only):
            return []
        return [s for s in main_spans if s.kind != "import"]

    def normalize_and_assemble(self, imports, all_decl, logic, guards, main, docstring=None):
        future_imports = [s for s in imports if "from __future__" in s.text]
        regular_imports = [s for s in imports if s not in future_imports]

        regular_imports, import_symbols = normalize_imports(
            package_name=self.package_name,
            import_spans=regular_imports,
        )

        ordered = []
        blank_line = Span(kind="blank", text="\n")

        if docstring:
            ordered.append(docstring)
            ordered.append(blank_line)

        ordered.extend(future_imports)
        if future_imports:
            ordered.append(blank_line)

        ordered.extend(regular_imports)
        if regular_imports:
            ordered.append(blank_line)

        if all_decl:
            ordered.append(all_decl)
            ordered.append(blank_line)

        for s in logic + guards:
            ordered.append(s)
            ordered.append(blank_line)

        ordered.extend(main)

        return ordered, import_symbols

    def check_clashes(self, spans, import_symbols):
        if not self.ignore_clashes:
            seen = set(import_symbols)
            for span in spans:
                if span.kind in ("function", "class"):
                    header = span.text.lstrip()
                    if header.startswith("def "):
                        name = header[4:].split("(", 1)[0].strip()
                    elif header.startswith("class "):
                        name = header[6:].split("(", 1)[0].strip()
                    else:
                        continue
                    if name in seen:
                        raise DuplicateNameError(f"Duplicate top-level name: {name}")
                    seen.add(name)


    def get_final_output_spans(self):
        docstring, all_decl, root_imports, root_logic = self.gather_root_spans()
        module_spans = self.gather_module_spans()
        main_guards = self.gather_main_guard_spans()
        main_body = self.get_main_spans()

        imports = root_imports + [s for s in module_spans if s.kind == "import"]
        logic = root_logic + [s for s in module_spans if s.kind not in["import", "main_guard"]]

        spans, import_symbols = self.normalize_and_assemble(
            imports, all_decl, logic, main_guards, main_body, docstring
        )

        self.check_clashes(spans, import_symbols)
        return spans

class FlatteningModule:

    __slots__ = ("module", "path")

    def __init__(self, ctx : FlatteningContext, path: Path):
        if not path.is_file():
            raise PathError(f"FlatteningModule must be created from a file: {path}")

        try:
            relpath = path.relative_to(ctx.package_path)
        except ValueError:
            raise PathError(f"Path {path} is not inside package root {ctx.package_path}")

        if relpath == Path('.'):
            relpath = Path(ctx.package_path.name)
        if relpath.name == "__init__.py":
            self.module = ctx.package_name
        else:
            mod_suffix = str(relpath.with_suffix('')).replace('/', '.')
            self.module = ctx.package_name + "." + mod_suffix

        self.path = path

def dotted_member_of(dotted: str, module_list: List[str]) -> bool:
    if not module_list:
        return False
    for module in module_list:
        if dotted_of_module(module, dotted):
            return True
    return False

def dotted_of_module(module: str, dotted: str) -> bool:
    if dotted == module:
        return True
    if dotted.startswith(module + "."):
        return True
    return False

def normalize_a_module_name(module_name: str, package_name: str) -> str:
    if not isinstance(module_name, str):
        raise FlatteningError(f"module_name must be str, not {type(module_name)} : {module_name!r}")
    if module_name.startswith(package_name + ".") or module_name == package_name:
        return module_name
    else:
        return package_name + "." + module_name.lstrip('.')

def normalize_module_names(
    package_name: str,
    module_names: Union[str, List[str]]
) -> list[str]:
    if isinstance(module_names, str):
        module_names = [normalize_a_module_name(module_names, package_name)]
    if not isinstance(module_names, list):
        raise FlatteningError(f"module_names must be str or list of str, not {type(module_names)}")
    return [normalize_a_module_name(mod, package_name) for mod in module_names]

"""Functions for normalizing and rewriting import statements."""

"""
TODO: Add module-level docstring.
"""

try :
    from stdlib_list import stdlib_list
    STDLIB_MODULES = None
except ImportError:
    STDLIB_MODULES = {
        'ast', 'os', 'sys', 'math', 'json', 're', 'pathlib', 'collections',
        'typing', 'asyncio', 'threading', 'subprocess', 'itertools', 'functools',
        'http', 'email', 'unittest', 'logging', 'time', 'shutil',
        'contextlib', 'pickle', 'dataclasses', 'socket', 'inspect',
        'importlib', 'types', 'copy', 'errno', 'statistics',
        # and more... (expand as needed)
    }
    stdlib_list = False

DEFAULT_LINE_LENGTH = 80

LINE_LENGTH = DEFAULT_LINE_LENGTH

@dataclass(order=True)
class ImportEntry:
    """
    Note:
    - All None values are coerced to '' for sorting/equality purposes.
    - This guarantees compatibility with @dataclass(order=True).
    """
    module: str
    symbol: str
    asname: str
    is_plain_import: bool
    def __post_init__(self):
        # Explicitly coerce types
        """TODO: Add detailed docstring."""
        object.__setattr__(self, 'module', self.module or '')
        object.__setattr__(self, 'symbol', self.symbol or '')
        object.__setattr__(self, 'asname', self.asname or '')

IE = ImportEntry

def normalize_imports(package_name: str, import_spans: List[Span], pyver=None) -> Tuple[List[Span], List[str]]:
    """
    Normalize import spans:
    - Eliminate all relative imports.
    - Eliminate all absolute local imports matching the project_package.
    - Deduplicate surviving imports by (module, alias-or-symbol).
    - Regroup into from-import lines.
    - Apply line-wrapping for >80 char lines.
    - Group stdlib and third-party imports separately.
    Returns a tuple of (list of formatted import spans, list of imported global names).
    """
    imports = []
    for span in import_spans:
        tree = ast.parse(span.text)
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                if node.level > 0:
                    continue  # Eliminate relative imports
                if node.module and ( node.module == package_name
                                  or node.module.startswith(package_name+'.') ):
                    continue  # Eliminate local absolute imports
                module = node.module
                for alias in node.names:
                    imports.append(IE(module, alias.name, alias.asname, is_plain_import=False))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
                    if ( module == package_name
                      or module.startswith(package_name+'.') ):
                        continue  # Eliminate local absolute imports
                    imports.append(IE(module, alias.name, alias.asname, is_plain_import=True))

    # Deduplicate by (module, alias-or-symbol)
    names = {}
    seen = set()
    module_to_symbols = defaultdict(list)
    imported_names = []

    for entry in imports:
        # use alias if present, else symbol, else module stem
        name = entry.asname or entry.symbol or entry.module.split('.')[-1]
        key = (entry.module, name)
        if key in seen:
            continue
        if name in names:
            raise ImportNormalizationError(f"name clash importing `{name}` from {entry.module}, already imported from {names[name]}")
        seen.add(key)
        names[name] = entry.module
        imported_names.append(name)
        module_to_symbols[entry.module].append(entry)

    stdlib_imports = {}
    third_party_imports = {}

    for module, entries in module_to_symbols.items():
        if is_stdlib_module(module.split('.')[0], pyver=pyver):
            stdlib_imports[module] = entries
        else:
            third_party_imports[module] = entries

    output_spans = []

    for group in (stdlib_imports, third_party_imports):
        if not group:
            continue
        for module in sorted(group):
            entries = sorted(group[module])
            plain_entries = [e for e in entries if e.is_plain_import]
            from_entries  = [e for e in entries if not e.is_plain_import]
            if plain_entries:
                text = "\n".join(format_plain_import(plain_entries)) + '\n'
                output_spans.append(Span(kind="import", text=text))
            if from_entries:
                text = "\n".join(format_from_import(from_entries)) + '\n'
                output_spans.append(Span(kind="import", text=text))
        output_spans.append(Span(kind="blank", text="\n"))

    return output_spans, imported_names

    """TODO: Add detailed docstring."""

def format_plain_import(entries: List[ImportEntry]) -> List[str]:
    if not entries:
        return []
    # entries are (symbol, asname), but for plain import, symbol is None
    imports = set()
    for e in entries:
        if e.asname:
            imports.add(f"{e.module} as {e.asname}")
        else:
            imports.add(f"{e.module}")
    return [ "import " + sym_expr for sym_expr in sorted(imports) ]

    """TODO: Add detailed docstring."""

def format_from_import(entries: List[ImportEntry]) -> List[str]:
    if not entries:
        return []
    symbols = set()
    for e in entries:
        if e.asname:
            symbols.add(f"{e.symbol} as {e.asname}")
        else:
            symbols.add(f"{e.symbol}")
    module = e.module
    if len(", ".join(sorted(symbols))) <= (LINE_LENGTH-len(f"from {module} import ")):
        return [f"from {module} import {', '.join(sorted(symbols))}"]
    parts = [f"from {module} import ("]
    for sym in sorted(symbols):
        parts.append(f"    {sym},")
    parts.append(")")
    return parts

    """TODO: Expand this docstring."""

def is_stdlib_module(module, pyver=None):
    """
    Check if a module is part of the standard library.
    """
    global STDLIB_MODULES
    if module in sys.builtin_module_names:
        return True
    if stdlib_list and pyver is not None:
        # If stdlib_list is available, use it to check for stdlib modules
        if STDLIB_MODULES is None:
            STDLIB_MODULES = stdlib_list(pyver)
        return module in STDLIB_MODULES
    return module in STDLIB_MODULES

# User configurable line length
    """TODO: Expand this docstring."""

def set_line_length(length: int):
    """
    Set the line length for formatting imports.
    """
    global LINE_LENGTH
    if length > 0:
        LINE_LENGTH = length
    else:
        raise ImportNormalizationError("`line_length` must be > 0")

# Get the current line length
    """TODO: Expand this docstring."""

def get_line_length() -> int:
    """
    Get the current line length for formatting imports.
    """
    return LINE_LENGTH

USAGE=r"""
Usage:
  pyonetrue [options] <input>
  pyonetrue (-h | --help)
  pyonetrue --version

Flatten Python package files into a well ordered, single module.

<input> can be a python package name, a directory or a file:
  package    The <package-root> via PYTHONPATH becomes the directory.
  directory  All Python files under the directory will be flattened.
  file       It will be ordered, fixes a poor ordering.

In all cases, the module is written to the specified output file or stdout.

A main guard is a block of code that is only executed when the module
is run as a script. It is typically used to test the module or to
provide a command-line interface. The main guard is usually
written as:

    if __name__ == '__main__':
        # code to execute when the module is run as a script
        pass

<package>/__main__.py is a special module that is executed when the
package is run as a script.  It is typically used to provide a command-line
interface to the package.  If such a module is present, it will be included
at the end of without reordering unless the --module-only option is used.  Other
__main__.py modules are not included by default.  If you want to include
one of them instead, you can use the --main-from option to specify the
sub-package from which to include __main__.py.

Default behavior is to :
* All relative imports are eliminated. Flattened output is fully self-contained.
* Main guards are discarded, but this can be changed with the --all-guards
  or --guards-from options.
* Write the output to stdout, but this can be changed with the --output
* Name clashes, duplicate top-level names, are not allowed by default.
* If `__main__.py` is being included, prepend shebang.

Options:
  -s, --shebang <shebang>  Prepend <shebang> if `__main__.py` is being appended.  [default: #!/usr/bin/env python3]
  -o, --output <file>      Write output to file (default: stdout).
  -M, --module-only        Build a pure module without an entry point, i.e. no
                           __main__ guard, no __main__.py, no CLI.
  --entry <entry>          Explicitly build for the given entry point.  May be
                           repeated. If omitted, all entry points are built.
  -m, --main-from <mod>    Include __main__.py from the specified sub-package.
                           Only one __main__.py module is allowed.
                           Incompatible with --module-only.
  -a, --all-guards         Include all __main__ guards. (default: discard)
  -g, --guards-from <mod>  Include __main__ guards only from <mod>.
  -E, --exclude <exclude>  Exclude specified packages or modules, comma separated.
  -i, --include <include>  Include specified packages or modules, comma separated.
  --ignore-clashes         Allow duplicate top-level names without error.
  -h, --help               Show this help message.
  --version                Show version.
  --show-cli-args          Show the command line arguments that would be passed to the
                           CLI and exit.  This is useful for debugging.
"""

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # For Python 3.11 and earlier

try :
    from pathlib import Path
except ImportError:
    from .vendor.pathlib import Path

__version__ = "0.7.1"

def discover_defined_entry_points(package_path: Path) -> list[str]:
    """Return entry point modules defined in a local pyproject.toml."""
    pyproject = package_path / "pyproject.toml"
    if not pyproject.exists():
        pyproject = package_path.parent / "pyproject.toml"
    entries = []
    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text())
            scripts = data.get("project", {}).get("scripts", {})
            for target in scripts.values():
                mod = str(target).split(":", 1)[0]
                entries.append(mod)
        except Exception:
            pass
    return entries

def main(argv=sys.argv):
    """Main entry point for the CLI tool.

    Parses command-line arguments, configures the FlatteningContext,
    executes the flattening process, and handles output.

    Args:
        argv (list of str): Command-line arguments (including program name).

    Returns:
        int: Exit code (0 on success, non-zero on error).

    Examples:
        >>> main(["pyonetrue", "my_package"])
        0
    """

    args = docopt(USAGE, argv=argv[1:], version=__version__)
    if args['--module-only'] and args['--main-from']:
        raise CLIOptionError("cannot specify both --module-only and --main-from")

    entries = args.get('--entry') or []
    if not isinstance(entries, list):
        entries = [entries] if entries else []
    
    entries = args.get('--entry')
    if entries and not isinstance(entries, list):
        entries = [entries]
    parsed_funcs = []
    for ent in entries or []:
        if ':' in ent:
            ent = ent.rsplit(':', 1)[1]
        elif '.' in ent:
            ent = ent.split('.')[-1]
        elif ent:
            ent = ent
        else:
            continue
        parsed_funcs.append(ent)
    ctx = FlatteningContext(
        package_path=args['<input>'],
        output=args.get('--output') or 'stdout',
        module_only=bool(args.get('--module-only')),
        main_from=args.get('--main-from', '').split(',') if args.get('--main-from') else [],
        guards_all=bool(args.get('--all-guards')),
        guards_from=args.get('--guards-from', '').split(',') if args.get('--guards-from') else [],
        ignore_clashes=bool(args.get('--ignore-clashes')),
        exclude=args.get('--exclude', '').split(',') if args.get('--exclude') else [],
        include=args.get('--include', '').split(',') if args.get('--include') else [],
        shebang=args.get('--shebang', '#!/usr/bin/env python3'),
        entry_points=entries,
    )

    if ctx.module_only and (ctx.main_from or ctx.entry_points):
        raise CLIOptionError("cannot specify --module-only with --main-from or --entry")

    if ctx.main_from and ctx.entry_points:
        raise CLIOptionError("cannot specify both --main-from and --entry")

    if not ctx.entry_points:
        ctx.entry_points = discover_defined_entry_points(Path(ctx.package_path))

    if not ctx.entry_points and not ctx.module_only:
        ctx.main_from = ctx.main_from[0] if ctx.main_from else None
        if not ctx.main_from:
            ctx.main_from = '__main__' # primary package

    if args['--show-cli-args']:
        print(f"CLI args:\n{ctx}")
        return 0

    entry_mods = ctx.entry_points or ([ctx.main_from] if ctx.main_from else [])
    if not entry_mods:
        entry_mods = [None]

    output_path = ctx.output
    if len(entry_mods) > 1 and output_path != "stdout":
        out_dir = Path(output_path)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = None

    for mod in entry_mods:
        sub_ctx = FlatteningContext(
            package_path=ctx.package_path,
            output=output_path,
            module_only=ctx.module_only,
            main_from=[mod] if mod else [],
            guards_all=ctx.guards_all,
            guards_from=ctx.guards_from,
            ignore_clashes=ctx.ignore_clashes,
            exclude=ctx.exclude,
            include=ctx.include,
            shebang=ctx.shebang,
        )

        sub_ctx.main_from = sub_ctx.main_from[0] if sub_ctx.main_from else None
        if sub_ctx.main_from:
            sub_ctx.module_only = False
        elif not sub_ctx.module_only:
            sub_ctx.main_from = "__main__"

        sub_ctx.discover_modules()
        sub_ctx.gather_main_guard_spans()
        spans = sub_ctx.get_final_output_spans()

        lines = []
        if sub_ctx.shebang:
            lines.append(sub_ctx.shebang.rstrip("\n") + "\n")
        lines.extend(span.text for span in spans)
        text = "".join(lines)

        if sub_ctx.output == "stdout":
            sys.stdout.write(text)
        else:
            if out_dir:
                fname = mod or "output"
                Path(out_dir / f"{fname}.py").write_text(text)
            else:
                Path(sub_ctx.output).write_text(text)

    return 0

"""Parsing Python source and extract top-level code spans."""

try :
    from pathlib import Path
except ImportError:
    from .vendor.pathlib import Path

class Span:
    """Represents a contiguous block of top-level code in the source file.

    Attributes:
        text (str): The exact source text of the span, including decorators or comments.
        kind (str): The category of the span, one of 'import', 'class', 'function', 'logic', or 'main_guard'.
    """
    def __init__(self, text: str, kind: str):
        """Initialize a Span with source text and its classification.

        Args:
            text (str): The source code text for this span.
            kind (str): The type of span (e.g., 'import', 'class', 'function', etc.).
        """
        self.text = text
        self.kind = kind  # 'import', 'class', 'function', 'logic', 'main_guard'

    def __repr__(self):
        """Return a representation showing kind and truncated text for debugging."""
        return f"Span(kind={self.kind!r}, text={self.text!r})"

def extract_spans(source: Union[str, Path], filename: str = '<unknown>') -> List[Span]:
    """Parse Python source to extract ordered top-level code spans.

    Args:
        source (str or Path): Raw Python source or path to a .py file.
        filename (str): Optional filename for AST parsing error messages.

    Returns:
        List[Span]: A list of Span objects representing each top-level section of code.

    Examples:
        >>> spans = extract_spans('x = 1\n')
        >>> isinstance(spans[0], Span)
        True
    """
    if isinstance(source, Path):
        source = source.read_text()

    lines = source.splitlines(keepends=True)
    tree = ast.parse(source, filename)
    spans: List[Span] = []

    for node in tree.body:
        start = node.lineno - 1
        end = node.end_lineno or node.lineno
        # Determine kind
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            kind = 'import'
        elif isinstance(node, ast.ClassDef):
            kind = 'class'
            # If it has decorators, we consider the decorator as part of it
            if node.decorator_list:
                start = node.decorator_list[0].lineno - 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = 'function'
            # If it has decorators, we consider the decorator as part of it
            if node.decorator_list:
                start = node.decorator_list[0].lineno - 1
        elif isinstance(node, ast.If):
            # Detect main guard: if __name__ == '__main__'
            test = node.test
            is_guard = (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == '__name__'
                and any(
                    isinstance(op, ast.Eq) for op in test.ops
                )
                and any(
                    isinstance(elt, ast.Constant) and elt.value == '__main__'
                    for elt in test.comparators
                )
            )
            kind = 'main_guard' if is_guard else 'logic'
        else:
            kind = 'logic'

        # Extract the text from the lines -- required to capture decorators
        spans.append(Span(''.join(lines[start:end]), kind))

    return spans

try:
    from collections.abc import Sequence
except ImportError:  # pragma: no cover - for older Python
    from collections import Sequence

try:
    from urllib import quote as urlquote, quote as urlquote_from_bytes
except ImportError:
    from urllib.parse import quote as urlquote, quote_from_bytes as urlquote_from_bytes

try:
    intern = intern
except NameError:
    intern = sys.intern

supports_symlinks = True

try:
    import nt
except ImportError:
    nt = None
else:
    if sys.getwindowsversion()[:2] >= (6, 0) and sys.version_info >= (3, 2):
        from nt import _getfinalpathname
    else:
        supports_symlinks = False
        _getfinalpathname = None

__all__ = [
    "PurePath", "PurePosixPath", "PureWindowsPath",
    "Path", "PosixPath", "WindowsPath",
    ]

def _is_wildcard_pattern(pat):
    # Whether this pattern needs actual matching using fnmatch, or can
    # be looked up directly as a file.
    return "*" in pat or "?" in pat or "[" in pat

class _Flavour(object):
    """A flavour implements a particular (platform-specific) set of path
    semantics."""

    def __init__(self):
        self.join = self.sep.join

    def parse_parts(self, parts):
        parsed = []
        sep = self.sep
        altsep = self.altsep
        drv = root = ''
        it = reversed(parts)
        for part in it:
            if not part:
                continue
            if altsep:
                part = part.replace(altsep, sep)
            drv, root, rel = self.splitroot(part)
            if sep in rel:
                for x in reversed(rel.split(sep)):
                    if x and x != '.':
                        parsed.append(intern(x))
            else:
                if rel and rel != '.':
                    parsed.append(intern(rel))
            if drv or root:
                if not drv:
                    # If no drive is present, try to find one in the previous
                    # parts. This makes the result of parsing e.g.
                    # ("C:", "/", "a") reasonably intuitive.
                    for part in it:
                        drv = self.splitroot(part)[0]
                        if drv:
                            break
                break
        if drv or root:
            parsed.append(drv + root)
        parsed.reverse()
        return drv, root, parsed

    def join_parsed_parts(self, drv, root, parts, drv2, root2, parts2):
        """
        Join the two paths represented by the respective
        (drive, root, parts) tuples.  Return a new (drive, root, parts) tuple.
        """
        if root2:
            if not drv2 and drv:
                return drv, root2, [drv + root2] + parts2[1:]
        elif drv2:
            if drv2 == drv or self.casefold(drv2) == self.casefold(drv):
                # Same drive => second path is relative to the first
                return drv, root, parts + parts2[1:]
        else:
            # Second path is non-anchored (common case)
            return drv, root, parts + parts2
        return drv2, root2, parts2

class _WindowsFlavour(_Flavour):
    # Reference for Windows paths can be found at
    # http://msdn.microsoft.com/en-us/library/aa365247%28v=vs.85%29.aspx

    sep = '\\'
    altsep = '/'
    has_drv = True
    pathmod = ntpath

    is_supported = (nt is not None)

    drive_letters = (
        set(chr(x) for x in range(ord('a'), ord('z') + 1)) |
        set(chr(x) for x in range(ord('A'), ord('Z') + 1))
    )
    ext_namespace_prefix = '\\\\?\\'

    reserved_names = (
        {'CON', 'PRN', 'AUX', 'NUL'} |
        {'COM%d' % i for i in range(1, 10)} |
        {'LPT%d' % i for i in range(1, 10)}
        )

    # Interesting findings about extended paths:
    # - '\\?\c:\a', '//?/c:\a' and '//?/c:/a' are all supported
    #   but '\\?\c:/a' is not
    # - extended paths are always absolute; "relative" extended paths will
    #   fail.

    def splitroot(self, part, sep=sep):
        first = part[0:1]
        second = part[1:2]
        if (second == sep and first == sep):
            # XXX extended paths should also disable the collapsing of "."
            # components (according to MSDN docs).
            prefix, part = self._split_extended_path(part)
            first = part[0:1]
            second = part[1:2]
        else:
            prefix = ''
        third = part[2:3]
        if (second == sep and first == sep and third != sep):
            # is a UNC path:
            # vvvvvvvvvvvvvvvvvvvvv root
            # \\machine\mountpoint\directory\etc\...
            #            directory ^^^^^^^^^^^^^^
            index = part.find(sep, 2)
            if index != -1:
                index2 = part.find(sep, index + 1)
                # a UNC path can't have two slashes in a row
                # (after the initial two)
                if index2 != index + 1:
                    if index2 == -1:
                        index2 = len(part)
                    if prefix:
                        return prefix + part[1:index2], sep, part[index2+1:]
                    else:
                        return part[:index2], sep, part[index2+1:]
        drv = root = ''
        if second == ':' and first in self.drive_letters:
            drv = part[:2]
            part = part[2:]
            first = third
        if first == sep:
            root = first
            part = part.lstrip(sep)
        return prefix + drv, root, part

    def casefold(self, s):
        return s.lower()

    def casefold_parts(self, parts):
        return [p.lower() for p in parts]

    def resolve(self, path):
        s = str(path)
        if not s:
            return os.getcwd()
        if _getfinalpathname is not None:
            return self._ext_to_normal(_getfinalpathname(s))
        # Means fallback on absolute
        return None

    def _split_extended_path(self, s, ext_prefix=ext_namespace_prefix):
        prefix = ''
        if s.startswith(ext_prefix):
            prefix = s[:4]
            s = s[4:]
            if s.startswith('UNC\\'):
                prefix += s[:3]
                s = '\\' + s[3:]
        return prefix, s

    def _ext_to_normal(self, s):
        # Turn back an extended path into a normal DOS-like path
        return self._split_extended_path(s)[1]

    def is_reserved(self, parts):
        # NOTE: the rules for reserved names seem somewhat complicated
        # (e.g. r"..\NUL" is reserved but not r"foo\NUL").
        # We err on the side of caution and return True for paths which are
        # not considered reserved by Windows.
        if not parts:
            return False
        if parts[0].startswith('\\\\'):
            # UNC paths are never reserved
            return False
        return parts[-1].partition('.')[0].upper() in self.reserved_names

    def make_uri(self, path):
        # Under Windows, file URIs use the UTF-8 encoding.
        drive = path.drive
        if len(drive) == 2 and drive[1] == ':':
            # It's a path on a local drive => 'file:///c:/a/b'
            rest = path.as_posix()[2:].lstrip('/')
            return 'file:///%s/%s' % (
                drive, urlquote_from_bytes(rest.encode('utf-8')))
        else:
            # It's a path on a network drive => 'file://host/share/a/b'
            return 'file:' + urlquote_from_bytes(path.as_posix().encode('utf-8'))

class _PosixFlavour(_Flavour):
    sep = '/'
    altsep = ''
    has_drv = False
    pathmod = posixpath

    is_supported = (os.name != 'nt')

    def splitroot(self, part, sep=sep):
        if part and part[0] == sep:
            stripped_part = part.lstrip(sep)
            # According to POSIX path resolution:
            # http://pubs.opengroup.org/onlinepubs/009695399/basedefs/xbd_chap04.html#tag_04_11
            # "A pathname that begins with two successive slashes may be
            # interpreted in an implementation-defined manner, although more
            # than two leading slashes shall be treated as a single slash".
            if len(part) - len(stripped_part) == 2:
                return '', sep * 2, stripped_part
            else:
                return '', sep, stripped_part
        else:
            return '', '', part

    def casefold(self, s):
        return s

    def casefold_parts(self, parts):
        return parts

    def resolve(self, path):
        sep = self.sep
        def split(p):
            return [x for x in p.split(sep) if x]
        def absparts(p):
            # Our own abspath(), since the posixpath one makes
            # the mistake of "normalizing" the path without resolving the
            # symlinks first.
            if not p.startswith(sep):
                return split(os.getcwd()) + split(p)
            else:
                return split(p)
        parts = absparts(str(path))[::-1]
        accessor = path._accessor
        resolved = cur = ""
        symlinks = {}
        while parts:
            part = parts.pop()
            cur = resolved + sep + part
            if cur in symlinks and symlinks[cur] <= len(parts):
                # We've already seen the symlink and there's not less
                # work to do than the last time.
                raise RuntimeError("Symlink loop from %r" % cur)
            try:
                target = accessor.readlink(cur)
            except OSError as e:
                if e.errno != EINVAL:
                    raise
                # Not a symlink
                resolved = cur
            else:
                # Take note of remaining work from this symlink
                symlinks[cur] = len(parts)
                if target.startswith(sep):
                    # Symlink points to absolute path
                    resolved = ""
                parts.extend(split(target)[::-1])
        return resolved or sep

    def is_reserved(self, parts):
        return False

    def make_uri(self, path):
        # We represent the path using the local filesystem encoding,
        # for portability to other applications.
        bpath = bytes(path)
        return 'file://' + urlquote_from_bytes(bpath)

_windows_flavour = _WindowsFlavour()

_posix_flavour = _PosixFlavour()

class _Accessor:
    """An accessor implements a particular (system-specific or not) way of
    accessing paths on the filesystem."""

class _NormalAccessor(_Accessor):

    def _wrap_strfunc(strfunc):
        @functools.wraps(strfunc)
        def wrapped(pathobj, *args):
            return strfunc(str(pathobj), *args)
        return staticmethod(wrapped)

    def _wrap_binary_strfunc(strfunc):
        @functools.wraps(strfunc)
        def wrapped(pathobjA, pathobjB, *args):
            return strfunc(str(pathobjA), str(pathobjB), *args)
        return staticmethod(wrapped)

    stat = _wrap_strfunc(os.stat)

    lstat = _wrap_strfunc(os.lstat)

    open = _wrap_strfunc(os.open)

    listdir = _wrap_strfunc(os.listdir)

    chmod = _wrap_strfunc(os.chmod)

    if hasattr(os, "lchmod"):
        lchmod = _wrap_strfunc(os.lchmod)
    else:
        def lchmod(self, pathobj, mode):
            raise NotImplementedError("lchmod() not available on this system")

    mkdir = _wrap_strfunc(os.mkdir)

    unlink = _wrap_strfunc(os.unlink)

    rmdir = _wrap_strfunc(os.rmdir)

    rename = _wrap_binary_strfunc(os.rename)

    if sys.version_info >= (3, 3):
        replace = _wrap_binary_strfunc(os.replace)

    if nt:
        if supports_symlinks:
            symlink = _wrap_binary_strfunc(os.symlink)
        else:
            def symlink(a, b, target_is_directory):
                raise NotImplementedError("symlink() not available on this system")
    else:
        # Under POSIX, os.symlink() takes two args
        @staticmethod
        def symlink(a, b, target_is_directory):
            return os.symlink(str(a), str(b))

    utime = _wrap_strfunc(os.utime)

    # Helper for resolve()
    def readlink(self, path):
        return os.readlink(path)

_normal_accessor = _NormalAccessor()

@contextmanager
def _cached(func):
    try:
        func.__cached__
        yield func
    except AttributeError:
        cache = {}
        def wrapper(*args):
            try:
                return cache[args]
            except KeyError:
                value = cache[args] = func(*args)
                return value
        wrapper.__cached__ = True
        try:
            yield wrapper
        finally:
            cache.clear()

def _make_selector(pattern_parts):
    pat = pattern_parts[0]
    child_parts = pattern_parts[1:]
    if pat == '**':
        cls = _RecursiveWildcardSelector
    elif '**' in pat:
        raise ValueError("Invalid pattern: '**' can only be an entire path component")
    elif _is_wildcard_pattern(pat):
        cls = _WildcardSelector
    else:
        cls = _PreciseSelector
    return cls(pat, child_parts)

if hasattr(functools, "lru_cache"):
    _make_selector = functools.lru_cache()(_make_selector)

class _Selector:
    """A selector matches a specific glob pattern part against the children
    of a given path."""

    def __init__(self, child_parts):
        self.child_parts = child_parts
        if child_parts:
            self.successor = _make_selector(child_parts)
        else:
            self.successor = _TerminatingSelector()

    def select_from(self, parent_path):
        """Iterate over all child paths of `parent_path` matched by this
        selector.  This can contain parent_path itself."""
        path_cls = type(parent_path)
        is_dir = path_cls.is_dir
        exists = path_cls.exists
        listdir = parent_path._accessor.listdir
        return self._select_from(parent_path, is_dir, exists, listdir)

class _TerminatingSelector:

    def _select_from(self, parent_path, is_dir, exists, listdir):
        yield parent_path

class _PreciseSelector(_Selector):

    def __init__(self, name, child_parts):
        self.name = name
        _Selector.__init__(self, child_parts)

    def _select_from(self, parent_path, is_dir, exists, listdir):
        if not is_dir(parent_path):
            return
        path = parent_path._make_child_relpath(self.name)
        if exists(path):
            for p in self.successor._select_from(path, is_dir, exists, listdir):
                yield p

class _WildcardSelector(_Selector):

    def __init__(self, pat, child_parts):
        self.pat = re.compile(fnmatch.translate(pat))
        _Selector.__init__(self, child_parts)

    def _select_from(self, parent_path, is_dir, exists, listdir):
        if not is_dir(parent_path):
            return
        cf = parent_path._flavour.casefold
        for name in listdir(parent_path):
            casefolded = cf(name)
            if self.pat.match(casefolded):
                path = parent_path._make_child_relpath(name)
                for p in self.successor._select_from(path, is_dir, exists, listdir):
                    yield p

class _RecursiveWildcardSelector(_Selector):

    def __init__(self, pat, child_parts):
        _Selector.__init__(self, child_parts)

    def _iterate_directories(self, parent_path, is_dir, listdir):
        yield parent_path
        for name in listdir(parent_path):
            path = parent_path._make_child_relpath(name)
            if is_dir(path):
                for p in self._iterate_directories(path, is_dir, listdir):
                    yield p

    def _select_from(self, parent_path, is_dir, exists, listdir):
        if not is_dir(parent_path):
            return
        with _cached(listdir) as listdir:
            yielded = set()
            try:
                successor_select = self.successor._select_from
                for starting_point in self._iterate_directories(parent_path, is_dir, listdir):
                    for p in successor_select(starting_point, is_dir, exists, listdir):
                        if p not in yielded:
                            yield p
                            yielded.add(p)
            finally:
                yielded.clear()

class _PathParents(Sequence):
    """This object provides sequence-like access to the logical ancestors
    of a path.  Don't try to construct it yourself."""
    __slots__ = ('_pathcls', '_drv', '_root', '_parts')

    def __init__(self, path):
        # We don't store the instance to avoid reference cycles
        self._pathcls = type(path)
        self._drv = path._drv
        self._root = path._root
        self._parts = path._parts

    def __len__(self):
        if self._drv or self._root:
            return len(self._parts) - 1
        else:
            return len(self._parts)

    def __getitem__(self, idx):
        if idx < 0 or idx >= len(self):
            raise IndexError(idx)
        return self._pathcls._from_parsed_parts(self._drv, self._root,
                                                self._parts[:-idx - 1])

    def __repr__(self):
        return "<{}.parents>".format(self._pathcls.__name__)

class PurePath(object):
    """PurePath represents a filesystem path and offers operations which
    don't imply any actual filesystem I/O.  Depending on your system,
    instantiating a PurePath will return either a PurePosixPath or a
    PureWindowsPath object.  You can also instantiate either of these classes
    directly, regardless of your system.
    """
    __slots__ = (
        '_drv', '_root', '_parts',
        '_str', '_hash', '_pparts', '_cached_cparts',
    )

    def __new__(cls, *args):
        """Construct a PurePath from one or several strings and or existing
        PurePath objects.  The strings and path objects are combined so as
        to yield a canonicalized path, which is incorporated into the
        new PurePath object.
        """
        if cls is PurePath:
            cls = PureWindowsPath if os.name == 'nt' else PurePosixPath
        return cls._from_parts(args)

    def __reduce__(self):
        # Using the parts tuple helps share interned path parts
        # when pickling related paths.
        return (self.__class__, tuple(self._parts))

    @classmethod
    def _parse_args(cls, args):
        # This is useful when you don't want to create an instance, just
        # canonicalize some constructor arguments.
        parts = []
        for a in args:
            if isinstance(a, PurePath):
                parts += a._parts
            elif isinstance(a, str):
                # Assuming a str
                parts.append(a)
            else:
                raise TypeError(
                    "argument should be a path or str object, not %r"
                    % type(a))
        return cls._flavour.parse_parts(parts)

    @classmethod
    def _from_parts(cls, args, init=True):
        # We need to call _parse_args on the instance, so as to get the
        # right flavour.
        self = object.__new__(cls)
        drv, root, parts = self._parse_args(args)
        self._drv = drv
        self._root = root
        self._parts = parts
        if init:
            self._init()
        return self

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts, init=True):
        self = object.__new__(cls)
        self._drv = drv
        self._root = root
        self._parts = parts
        if init:
            self._init()
        return self

    @classmethod
    def _format_parsed_parts(cls, drv, root, parts):
        if drv or root:
            return drv + root + cls._flavour.join(parts[1:])
        else:
            return cls._flavour.join(parts)

    def _init(self):
        # Overriden in concrete Path
        pass

    def _make_child(self, args):
        drv, root, parts = self._parse_args(args)
        drv, root, parts = self._flavour.join_parsed_parts(
            self._drv, self._root, self._parts, drv, root, parts)
        return self._from_parsed_parts(drv, root, parts)

    def __str__(self):
        """Return the string representation of the path, suitable for
        passing to system calls."""
        try:
            return self._str
        except AttributeError:
            self._str = self._format_parsed_parts(self._drv, self._root,
                                                  self._parts) or '.'
            return self._str

    def as_posix(self):
        """Return the string representation of the path with forward (/)
        slashes."""
        f = self._flavour
        return str(self).replace(f.sep, '/')

    def __bytes__(self):
        """Return the bytes representation of the path.  This is only
        recommended to use under Unix."""
        if sys.version_info < (3, 2):
            raise NotImplementedError("needs Python 3.2 or later")
        return os.fsencode(str(self))

    def __fspath__(self):
        return str(self)

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.as_posix())

    def as_uri(self):
        """Return the path as a 'file' URI."""
        if not self.is_absolute():
            raise ValueError("relative path can't be expressed as a file URI")
        return self._flavour.make_uri(self)

    @property
    def _cparts(self):
        # Cached casefolded parts, for hashing and comparison
        try:
            return self._cached_cparts
        except AttributeError:
            self._cached_cparts = self._flavour.casefold_parts(self._parts)
            return self._cached_cparts

    def __eq__(self, other):
        if not isinstance(other, PurePath):
            return NotImplemented
        return self._cparts == other._cparts and self._flavour is other._flavour

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(tuple(self._cparts))
            return self._hash

    def __lt__(self, other):
        if not isinstance(other, PurePath) or self._flavour is not other._flavour:
            return NotImplemented
        return self._cparts < other._cparts

    def __le__(self, other):
        if not isinstance(other, PurePath) or self._flavour is not other._flavour:
            return NotImplemented
        return self._cparts <= other._cparts

    def __gt__(self, other):
        if not isinstance(other, PurePath) or self._flavour is not other._flavour:
            return NotImplemented
        return self._cparts > other._cparts

    def __ge__(self, other):
        if not isinstance(other, PurePath) or self._flavour is not other._flavour:
            return NotImplemented
        return self._cparts >= other._cparts

    drive = property(attrgetter('_drv'),
                     doc="""The drive prefix (letter or UNC path), if any.""")

    root = property(attrgetter('_root'),
                    doc="""The root of the path, if any.""")

    @property
    def anchor(self):
        """The concatenation of the drive and root, or ''."""
        anchor = self._drv + self._root
        return anchor

    @property
    def name(self):
        """The final path component, if any."""
        parts = self._parts
        if len(parts) == (1 if (self._drv or self._root) else 0):
            return ''
        return parts[-1]

    @property
    def suffix(self):
        """The final component's last suffix, if any."""
        name = self.name
        i = name.rfind('.')
        if 0 < i < len(name) - 1:
            return name[i:]
        else:
            return ''

    @property
    def suffixes(self):
        """A list of the final component's suffixes, if any."""
        name = self.name
        if name.endswith('.'):
            return []
        name = name.lstrip('.')
        return ['.' + suffix for suffix in name.split('.')[1:]]

    @property
    def stem(self):
        """The final path component, minus its last suffix."""
        name = self.name
        i = name.rfind('.')
        if 0 < i < len(name) - 1:
            return name[:i]
        else:
            return name

    def with_name(self, name):
        """Return a new path with the file name changed."""
        if not self.name:
            raise ValueError("%r has an empty name" % (self,))
        return self._from_parsed_parts(self._drv, self._root,
                                       self._parts[:-1] + [name])

    def with_suffix(self, suffix):
        """Return a new path with the file suffix changed (or added, if none)."""
        # XXX if suffix is None, should the current suffix be removed?
        name = self.name
        if not name:
            raise ValueError("%r has an empty name" % (self,))
        old_suffix = self.suffix
        if not old_suffix:
            name = name + suffix
        else:
            name = name[:-len(old_suffix)] + suffix
        return self._from_parsed_parts(self._drv, self._root,
                                       self._parts[:-1] + [name])

    def relative_to(self, *other):
        """Return the relative path to another path identified by the passed
        arguments.  If the operation is not possible (because this is not
        a subpath of the other path), raise ValueError.
        """
        # For the purpose of this method, drive and root are considered
        # separate parts, i.e.:
        #   Path('c:/').relative_to('c:')  gives Path('/')
        #   Path('c:/').relative_to('/')   raise ValueError
        if not other:
            raise TypeError("need at least one argument")
        parts = self._parts
        drv = self._drv
        root = self._root
        if drv or root:
            if root:
                abs_parts = [drv, root] + parts[1:]
            else:
                abs_parts = [drv] + parts[1:]
        else:
            abs_parts = parts
        to_drv, to_root, to_parts = self._parse_args(other)
        if to_drv or to_root:
            if to_root:
                to_abs_parts = [to_drv, to_root] + to_parts[1:]
            else:
                to_abs_parts = [to_drv] + to_parts[1:]
        else:
            to_abs_parts = to_parts
        n = len(to_abs_parts)
        if n == 0 and (drv or root) or abs_parts[:n] != to_abs_parts:
            formatted = self._format_parsed_parts(to_drv, to_root, to_parts)
            raise ValueError("{!r} does not start with {!r}"
                             .format(str(self), str(formatted)))
        return self._from_parsed_parts('', '', abs_parts[n:])

    @property
    def parts(self):
        """An object providing sequence-like access to the
        components in the filesystem path."""
        # We cache the tuple to avoid building a new one each time .parts
        # is accessed.  XXX is this necessary?
        try:
            return self._pparts
        except AttributeError:
            self._pparts = tuple(self._parts)
            return self._pparts

    def joinpath(self, *args):
        """Combine this path with one or several arguments, and return a
        new path representing either a subpath (if all arguments are relative
        paths) or a totally different path (if one of the arguments is
        anchored).
        """
        return self._make_child(args)

    def __truediv__(self, key):
        return self._make_child((key,))

    def __rtruediv__(self, key):
        return self._from_parts([key] + self._parts)

    if sys.version_info < (3,):
        __div__ = __truediv__
        __rdiv__ = __rtruediv__
        del __truediv__, __rtruediv__

    @property
    def parent(self):
        """The logical parent of the path."""
        drv = self._drv
        root = self._root
        parts = self._parts
        if len(parts) == 1 and (drv or root):
            return self
        return self._from_parsed_parts(drv, root, parts[:-1])

    @property
    def parents(self):
        """A sequence of this path's logical parents."""
        return _PathParents(self)

    def is_absolute(self):
        """True if the path is absolute (has both a root and, if applicable,
        a drive)."""
        if not self._root:
            return False
        return not self._flavour.has_drv or bool(self._drv)

    def is_reserved(self):
        """Return True if the path contains one of the special names reserved
        by the system, if any."""
        return self._flavour.is_reserved(self._parts)

    def match(self, path_pattern):
        """
        Return True if this path matches the given pattern.
        """
        cf = self._flavour.casefold
        path_pattern = cf(path_pattern)
        drv, root, pat_parts = self._flavour.parse_parts((path_pattern,))
        if not pat_parts:
            raise ValueError("empty pattern")
        if drv and drv != cf(self._drv):
            return False
        if root and root != cf(self._root):
            return False
        parts = self._cparts
        if drv or root:
            if len(pat_parts) != len(parts):
                return False
            pat_parts = pat_parts[1:]
        elif len(pat_parts) > len(parts):
            return False
        for part, pat in zip(reversed(parts), reversed(pat_parts)):
            if not fnmatch.fnmatchcase(part, pat):
                return False
        return True

class PurePosixPath(PurePath):
    _flavour = _posix_flavour
    __slots__ = ()

class PureWindowsPath(PurePath):
    _flavour = _windows_flavour
    __slots__ = ()

class Path(PurePath):
    __slots__ = (
        '_accessor',
    )

    def __new__(cls, *args, **kwargs):
        if cls is Path:
            cls = WindowsPath if os.name == 'nt' else PosixPath
        self = cls._from_parts(args, init=False)
        if not self._flavour.is_supported:
            raise NotImplementedError("cannot instantiate %r on your system"
                                      % (cls.__name__,))
        self._init()
        return self

    def _init(self,
              # Private non-constructor arguments
              template=None,
              ):
        if template is not None:
            self._accessor = template._accessor
        else:
            self._accessor = _normal_accessor

    def _make_child_relpath(self, part):
        # This is an optimization used for dir walking.  `part` must be
        # a single part relative to this path.
        parts = self._parts + [part]
        return self._from_parsed_parts(self._drv, self._root, parts)

    def _opener(self, name, flags, mode=0o666):
        # A stub for the opener argument to built-in open()
        return self._accessor.open(self, flags, mode)

    def _raw_open(self, flags, mode=0o777):
        """
        Open the file pointed by this path and return a file descriptor,
        as os.open() does.
        """
        return self._accessor.open(self, flags, mode)

    # Public API

    @classmethod
    def cwd(cls):
        """Return a new path pointing to the current working directory
        (as returned by os.getcwd()).
        """
        return cls(os.getcwd())

    def iterdir(self):
        """Iterate over the files in this directory.  Does not yield any
        result for the special paths '.' and '..'.
        """
        for name in self._accessor.listdir(self):
            if name in {'.', '..'}:
                # Yielding a path object for these makes little sense
                continue
            yield self._make_child_relpath(name)

    def glob(self, pattern):
        """Iterate over this subtree and yield all existing files (of any
        kind, including directories) matching the given pattern.
        """
        pattern = self._flavour.casefold(pattern)
        drv, root, pattern_parts = self._flavour.parse_parts((pattern,))
        if drv or root:
            raise NotImplementedError("Non-relative patterns are unsupported")
        selector = _make_selector(tuple(pattern_parts))
        for p in selector.select_from(self):
            yield p

    def rglob(self, pattern):
        """Recursively yield all existing files (of any kind, including
        directories) matching the given pattern, anywhere in this subtree.
        """
        pattern = self._flavour.casefold(pattern)
        drv, root, pattern_parts = self._flavour.parse_parts((pattern,))
        if drv or root:
            raise NotImplementedError("Non-relative patterns are unsupported")
        selector = _make_selector(("**",) + tuple(pattern_parts))
        for p in selector.select_from(self):
            yield p

    def absolute(self):
        """Return an absolute version of this path.  This function works
        even if the path doesn't point to anything.

        No normalization is done, i.e. all '.' and '..' will be kept along.
        Use resolve() to get the canonical path to a file.
        """
        # XXX untested yet!
        if self.is_absolute():
            return self
        # FIXME this must defer to the specific flavour (and, under Windows,
        # use nt._getfullpathname())
        obj = self._from_parts([os.getcwd()] + self._parts, init=False)
        obj._init(template=self)
        return obj

    def resolve(self):
        """
        Make the path absolute, resolving all symlinks on the way and also
        normalizing it (for example turning slashes into backslashes under
        Windows).
        """
        s = self._flavour.resolve(self)
        if s is None:
            # No symlink resolution => for consistency, raise an error if
            # the path doesn't exist or is forbidden
            self.stat()
            s = str(self.absolute())
        # Now we have no symlinks in the path, it's safe to normalize it.
        normed = self._flavour.pathmod.normpath(s)
        obj = self._from_parts((normed,), init=False)
        obj._init(template=self)
        return obj

    def stat(self):
        """
        Return the result of the stat() system call on this path, like
        os.stat() does.
        """
        return self._accessor.stat(self)

    def owner(self):
        """
        Return the login name of the file owner.
        """
        import pwd
        return pwd.getpwuid(self.stat().st_uid).pw_name

    def group(self):
        """
        Return the group name of the file gid.
        """
        import grp
        return grp.getgrgid(self.stat().st_gid).gr_name

    def open(self, mode='r', buffering=-1, encoding=None,
             errors=None, newline=None):
        """
        Open the file pointed by this path and return a file object, as
        the built-in open() function does.
        """
        if sys.version_info >= (3, 3):
            return io.open(str(self), mode, buffering, encoding, errors, newline,
                           opener=self._opener)
        else:
            return io.open(str(self), mode, buffering, encoding, errors, newline)

    def read_bytes(self):
        """Open the file in bytes mode, read it, and close the file."""
        with self.open(mode='rb') as f:
            return f.read()

    def read_text(self, encoding=None, errors=None):
        """Open the file in text mode, read it, and close the file."""
        with self.open(mode='r', encoding=encoding, errors=errors) as f:
            return f.read()

    def write_bytes(self, data):
        """Open the file in bytes mode, write to it, and close the file."""
        view = memoryview(data)
        with self.open(mode='wb') as f:
            return f.write(view)

    def write_text(self, data, encoding=None, errors=None, newline=None):
        """Open the file in text mode, write to it, and close the file."""
        if not isinstance(data, str):
            raise TypeError('data must be str, not %s' % data.__class__.__name__)
        with self.open(mode='w', encoding=encoding, errors=errors, newline=newline) as f:
            return f.write(data)

    def touch(self, mode=0o666, exist_ok=True):
        """
        Create this file with the given access mode, if it doesn't exist.
        """
        if exist_ok:
            # First try to bump modification time
            # Implementation note: GNU touch uses the UTIME_NOW option of
            # the utimensat() / futimens() functions.
            t = time.time()
            try:
                self._accessor.utime(self, (t, t))
            except OSError:
                # Avoid exception chaining
                pass
            else:
                return
        flags = os.O_CREAT | os.O_WRONLY
        if not exist_ok:
            flags |= os.O_EXCL
        fd = self._raw_open(flags, mode)
        os.close(fd)

    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        if not parents:
            try:
                self._accessor.mkdir(self, mode)
            except OSError as e:
                if not (exist_ok and e.errno == EEXIST):
                    raise
        else:
            try:
                self._accessor.mkdir(self, mode)
            except OSError as e:
                if e.errno == ENOENT:
                    self.parent.mkdir(mode, True, exist_ok)
                    try:
                        self._accessor.mkdir(self, mode)
                    except OSError as e2:
                        if not (exist_ok and e2.errno == EEXIST):
                            raise
                elif not (exist_ok and e.errno == EEXIST):
                    raise

    def chmod(self, mode):
        """
        Change the permissions of the path, like os.chmod().
        """
        self._accessor.chmod(self, mode)

    def lchmod(self, mode):
        """
        Like chmod(), except if the path points to a symlink, the symlink's
        permissions are changed, rather than its target's.
        """
        self._accessor.lchmod(self, mode)

    def unlink(self):
        """
        Remove this file or link.
        If the path is a directory, use rmdir() instead.
        """
        self._accessor.unlink(self)

    def rmdir(self):
        """
        Remove this directory.  The directory must be empty.
        """
        self._accessor.rmdir(self)

    def lstat(self):
        """
        Like stat(), except if the path points to a symlink, the symlink's
        status information is returned, rather than its target's.
        """
        return self._accessor.lstat(self)

    def rename(self, target):
        """
        Rename this path to the given path.
        """
        self._accessor.rename(self, target)

    def replace(self, target):
        """
        Rename this path to the given path, clobbering the existing
        destination if it exists.
        """
        if sys.version_info < (3, 3):
            raise NotImplementedError("replace() is only available "
                                      "with Python 3.3 and later")
        self._accessor.replace(self, target)

    def symlink_to(self, target, target_is_directory=False):
        """
        Make this path a symlink pointing to the given path.
        Note the order of arguments (self, target) is the reverse of os.symlink's.
        """
        self._accessor.symlink(target, self, target_is_directory)

    # Convenience functions for querying the stat results

    def exists(self):
        """
        Whether this path exists.
        """
        try:
            self.stat()
        except OSError as e:
            if e.errno != ENOENT:
                raise
            return False
        return True

    def is_dir(self):
        """
        Whether this path is a directory.
        """
        try:
            return S_ISDIR(self.stat().st_mode)
        except OSError as e:
            if e.errno != ENOENT:
                raise
            # Path doesn't exist or is a broken symlink
            # (see https://bitbucket.org/pitrou/pathlib/issue/12/)
            return False

    def is_file(self):
        """
        Whether this path is a regular file (also True for symlinks pointing
        to regular files).
        """
        try:
            return S_ISREG(self.stat().st_mode)
        except OSError as e:
            if e.errno != ENOENT:
                raise
            # Path doesn't exist or is a broken symlink
            # (see https://bitbucket.org/pitrou/pathlib/issue/12/)
            return False

    def is_symlink(self):
        """
        Whether this path is a symbolic link.
        """
        try:
            return S_ISLNK(self.lstat().st_mode)
        except OSError as e:
            if e.errno != ENOENT:
                raise
            # Path doesn't exist
            return False

    def is_block_device(self):
        """
        Whether this path is a block device.
        """
        try:
            return S_ISBLK(self.stat().st_mode)
        except OSError as e:
            if e.errno != ENOENT:
                raise
            # Path doesn't exist or is a broken symlink
            # (see https://bitbucket.org/pitrou/pathlib/issue/12/)
            return False

    def is_char_device(self):
        """
        Whether this path is a character device.
        """
        try:
            return S_ISCHR(self.stat().st_mode)
        except OSError as e:
            if e.errno != ENOENT:
                raise
            # Path doesn't exist or is a broken symlink
            # (see https://bitbucket.org/pitrou/pathlib/issue/12/)
            return False

    def is_fifo(self):
        """
        Whether this path is a FIFO.
        """
        try:
            return S_ISFIFO(self.stat().st_mode)
        except OSError as e:
            if e.errno != ENOENT:
                raise
            # Path doesn't exist or is a broken symlink
            # (see https://bitbucket.org/pitrou/pathlib/issue/12/)
            return False

    def is_socket(self):
        """
        Whether this path is a socket.
        """
        try:
            return S_ISSOCK(self.stat().st_mode)
        except OSError as e:
            if e.errno != ENOENT:
                raise
            # Path doesn't exist or is a broken symlink
            # (see https://bitbucket.org/pitrou/pathlib/issue/12/)
            return False

class PosixPath(Path, PurePosixPath):
    __slots__ = ()

class WindowsPath(Path, PureWindowsPath):
    __slots__ = ()

"""Pythonic command-line interface parser that will make you smile.

 * http://docopt.org
 * Repository and issue-tracker: https://github.com/docopt/docopt
 * Licensed under terms of MIT license (see LICENSE-MIT)
 * Copyright (c) 2013 Vladimir Keleshev, vladimir@keleshev.com

"""

__all__ = ['docopt']

__version__ = '0.6.2'

class DocoptLanguageError(Exception):

    """Error in construction of usage-message by developer."""

class DocoptExit(SystemExit):

    """Exit in case user invoked program with incorrect arguments."""

    usage = ''

    def __init__(self, message=''):
        SystemExit.__init__(self, (message + '\n' + self.usage).strip())

class Pattern(object):

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __hash__(self):
        return hash(repr(self))

    def fix(self):
        self.fix_identities()
        self.fix_repeating_arguments()
        return self

    def fix_identities(self, uniq=None):
        """Make pattern-tree tips point to same object if they are equal."""
        if not hasattr(self, 'children'):
            return self
        uniq = list(set(self.flat())) if uniq is None else uniq
        for i, c in enumerate(self.children):
            if not hasattr(c, 'children'):
                assert c in uniq
                self.children[i] = uniq[uniq.index(c)]
            else:
                c.fix_identities(uniq)

    def fix_repeating_arguments(self):
        """Fix elements that should accumulate/increment values."""
        either = [list(c.children) for c in self.either.children]
        for case in either:
            for e in [c for c in case if case.count(c) > 1]:
                if type(e) is Argument or type(e) is Option and e.argcount:
                    if e.value is None:
                        e.value = []
                    elif type(e.value) is not list:
                        e.value = e.value.split()
                if type(e) is Command or type(e) is Option and e.argcount == 0:
                    e.value = 0
        return self

    @property
    def either(self):
        """Transform pattern into an equivalent, with only top-level Either."""
        # Currently the pattern will not be equivalent, but more "narrow",
        # although good enough to reason about list arguments.
        ret = []
        groups = [[self]]
        while groups:
            children = groups.pop(0)
            types = [type(c) for c in children]
            if Either in types:
                either = [c for c in children if type(c) is Either][0]
                children.pop(children.index(either))
                for c in either.children:
                    groups.append([c] + children)
            elif Required in types:
                required = [c for c in children if type(c) is Required][0]
                children.pop(children.index(required))
                groups.append(list(required.children) + children)
            elif DocoptOptional in types:
                optional = [c for c in children if type(c) is DocoptOptional][0]
                children.pop(children.index(optional))
                groups.append(list(optional.children) + children)
            elif DocoptAnyOptions in types:
                optional = [c for c in children if type(c) is DocoptAnyOptions][0]
                children.pop(children.index(optional))
                groups.append(list(optional.children) + children)
            elif OneOrMore in types:
                oneormore = [c for c in children if type(c) is OneOrMore][0]
                children.pop(children.index(oneormore))
                groups.append(list(oneormore.children) * 2 + children)
            else:
                ret.append(children)
        return Either(*[Required(*e) for e in ret])

class ChildPattern(Pattern):

    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.name, self.value)

    def flat(self, *types):
        return [self] if not types or type(self) in types else []

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        pos, match = self.single_match(left)
        if match is None:
            return False, left, collected
        left_ = left[:pos] + left[pos + 1:]
        same_name = [a for a in collected if a.name == self.name]
        if type(self.value) in (int, list):
            if type(self.value) is int:
                increment = 1
            else:
                increment = ([match.value] if type(match.value) is str
                             else match.value)
            if not same_name:
                match.value = increment
                return True, left_, collected + [match]
            same_name[0].value += increment
            return True, left_, collected
        return True, left_, collected + [match]

class ParentPattern(Pattern):

    def __init__(self, *children):
        self.children = list(children)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ', '.join(repr(a) for a in self.children))

    def flat(self, *types):
        if type(self) in types:
            return [self]
        return sum([c.flat(*types) for c in self.children], [])

class Argument(ChildPattern):

    def single_match(self, left):
        for n, p in enumerate(left):
            if type(p) is Argument:
                return n, Argument(self.name, p.value)
        return None, None

    @classmethod
    def parse(class_, source):
        name = re.findall(r'(<\S*?>)', source)[0]
        value = re.findall(r'\[default: (.*)\]', source, flags=re.I)
        return class_(name, value[0] if value else None)

class Command(Argument):

    def __init__(self, name, value=False):
        self.name = name
        self.value = value

    def single_match(self, left):
        for n, p in enumerate(left):
            if type(p) is Argument:
                if p.value == self.name:
                    return n, Command(self.name, True)
                else:
                    break
        return None, None

class Option(ChildPattern):

    def __init__(self, short=None, long=None, argcount=0, value=False):
        assert argcount in (0, 1)
        self.short, self.long = short, long
        self.argcount, self.value = argcount, value
        self.value = None if value is False and argcount else value

    @classmethod
    def parse(class_, option_description):
        short, long, argcount, value = None, None, 0, False
        options, _, description = option_description.strip().partition('  ')
        options = options.replace(',', ' ').replace('=', ' ')
        for s in options.split():
            if s.startswith('--'):
                long = s
            elif s.startswith('-'):
                short = s
            else:
                argcount = 1
        if argcount:
            matched = re.findall(r'\[default: (.*)\]', description, flags=re.I)
            value = matched[0] if matched else None
        return class_(short, long, argcount, value)

    def single_match(self, left):
        for n, p in enumerate(left):
            if self.name == p.name:
                return n, p
        return None, None

    @property
    def name(self):
        return self.long or self.short

    def __repr__(self):
        return 'Option(%r, %r, %r, %r)' % (self.short, self.long,
                                           self.argcount, self.value)

class Required(ParentPattern):

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        l = left
        c = collected
        for p in self.children:
            matched, l, c = p.match(l, c)
            if not matched:
                return False, left, collected
        return True, l, c

class DocoptOptional(ParentPattern):

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        for p in self.children:
            m, left, collected = p.match(left, collected)
        return True, left, collected

class DocoptAnyOptions(DocoptOptional):

    """Marker/placeholder for [options] shortcut."""

class OneOrMore(ParentPattern):

    def match(self, left, collected=None):
        assert len(self.children) == 1
        collected = [] if collected is None else collected
        l = left
        c = collected
        l_ = None
        matched = True
        times = 0
        while matched:
            # could it be that something didn't match but changed l or c?
            matched, l, c = self.children[0].match(l, c)
            times += 1 if matched else 0
            if l_ == l:
                break
            l_ = l
        if times >= 1:
            return True, l, c
        return False, left, collected

class Either(ParentPattern):

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        outcomes = []
        for p in self.children:
            matched, _, _ = outcome = p.match(left, collected)
            if matched:
                outcomes.append(outcome)
        if outcomes:
            return min(outcomes, key=lambda outcome: len(outcome[1]))
        return False, left, collected

class TokenStream(list):

    def __init__(self, source, error):
        self += source.split() if hasattr(source, 'split') else source
        self.error = error

    def move(self):
        return self.pop(0) if len(self) else None

    def current(self):
        return self[0] if len(self) else None

def parse_long(tokens, options):
    """long ::= '--' chars [ ( ' ' | '=' ) chars ] ;"""
    long, eq, value = tokens.move().partition('=')
    assert long.startswith('--')
    value = None if eq == value == '' else value
    similar = [o for o in options if o.long == long]
    if tokens.error is DocoptExit and similar == []:  # if no exact match
        similar = [o for o in options if o.long and o.long.startswith(long)]
    if len(similar) > 1:  # might be simply specified ambiguously 2+ times?
        raise tokens.error('%s is not a unique prefix: %s?' %
                           (long, ', '.join(o.long for o in similar)))
    elif len(similar) < 1:
        argcount = 1 if eq == '=' else 0
        o = Option(None, long, argcount)
        options.append(o)
        if tokens.error is DocoptExit:
            o = Option(None, long, argcount, value if argcount else True)
    else:
        o = Option(similar[0].short, similar[0].long,
                   similar[0].argcount, similar[0].value)
        if o.argcount == 0:
            if value is not None:
                raise tokens.error('%s must not have an argument' % o.long)
        else:
            if value is None:
                if tokens.current() is None:
                    raise tokens.error('%s requires argument' % o.long)
                value = tokens.move()
        if tokens.error is DocoptExit:
            o.value = value if value is not None else True
    return [o]

def parse_shorts(tokens, options):
    """shorts ::= '-' ( chars )* [ [ ' ' ] chars ] ;"""
    token = tokens.move()
    assert token.startswith('-') and not token.startswith('--')
    left = token.lstrip('-')
    parsed = []
    while left != '':
        short, left = '-' + left[0], left[1:]
        similar = [o for o in options if o.short == short]
        if len(similar) > 1:
            raise tokens.error('%s is specified ambiguously %d times' %
                               (short, len(similar)))
        elif len(similar) < 1:
            o = Option(short, None, 0)
            options.append(o)
            if tokens.error is DocoptExit:
                o = Option(short, None, 0, True)
        else:  # why copying is necessary here?
            o = Option(short, similar[0].long,
                       similar[0].argcount, similar[0].value)
            value = None
            if o.argcount != 0:
                if left == '':
                    if tokens.current() is None:
                        raise tokens.error('%s requires argument' % short)
                    value = tokens.move()
                else:
                    value = left
                    left = ''
            if tokens.error is DocoptExit:
                o.value = value if value is not None else True
        parsed.append(o)
    return parsed

def parse_pattern(source, options):
    tokens = TokenStream(re.sub(r'([\[\]\(\)\|]|\.\.\.)', r' \1 ', source),
                         DocoptLanguageError)
    result = parse_expr(tokens, options)
    if tokens.current() is not None:
        raise tokens.error('unexpected ending: %r' % ' '.join(tokens))
    return Required(*result)

def parse_expr(tokens, options):
    """expr ::= seq ( '|' seq )* ;"""
    seq = parse_seq(tokens, options)
    if tokens.current() != '|':
        return seq
    result = [Required(*seq)] if len(seq) > 1 else seq
    while tokens.current() == '|':
        tokens.move()
        seq = parse_seq(tokens, options)
        result += [Required(*seq)] if len(seq) > 1 else seq
    return [Either(*result)] if len(result) > 1 else result

def parse_seq(tokens, options):
    """seq ::= ( atom [ '...' ] )* ;"""
    result = []
    while tokens.current() not in [None, ']', ')', '|']:
        atom = parse_atom(tokens, options)
        if tokens.current() == '...':
            atom = [OneOrMore(*atom)]
            tokens.move()
        result += atom
    return result

def parse_atom(tokens, options):
    """atom ::= '(' expr ')' | '[' expr ']' | 'options'
             | long | shorts | argument | command ;
    """
    token = tokens.current()
    result = []
    if token in '([':
        tokens.move()
        matching, pattern = {'(': [')', Required], '[': [']', DocoptOptional]}[token]
        result = pattern(*parse_expr(tokens, options))
        if tokens.move() != matching:
            raise tokens.error("unmatched '%s'" % token)
        return [result]
    elif token == 'options':
        tokens.move()
        return [DocoptAnyOptions()]
    elif token.startswith('--') and token != '--':
        return parse_long(tokens, options)
    elif token.startswith('-') and token not in ('-', '--'):
        return parse_shorts(tokens, options)
    elif token.startswith('<') and token.endswith('>') or token.isupper():
        return [Argument(tokens.move())]
    else:
        return [Command(tokens.move())]

def parse_argv(tokens, options, options_first=False):
    """Parse command-line argument vector.

    If options_first:
        argv ::= [ long | shorts ]* [ argument ]* [ '--' [ argument ]* ] ;
    else:
        argv ::= [ long | shorts | argument ]* [ '--' [ argument ]* ] ;

    """
    parsed = []
    while tokens.current() is not None:
        if tokens.current() == '--':
            return parsed + [Argument(None, v) for v in tokens]
        elif tokens.current().startswith('--'):
            parsed += parse_long(tokens, options)
        elif tokens.current().startswith('-') and tokens.current() != '-':
            parsed += parse_shorts(tokens, options)
        elif options_first:
            return parsed + [Argument(None, v) for v in tokens]
        else:
            parsed.append(Argument(None, tokens.move()))
    return parsed

def parse_defaults(doc):
    # in python < 2.7 you can't pass flags=re.MULTILINE
    split = re.split(r'\n *(<\S+?>|-\S+?)', doc)[1:]
    split = [s1 + s2 for s1, s2 in zip(split[::2], split[1::2])]
    options = [Option.parse(s) for s in split if s.startswith('-')]
    #arguments = [Argument.parse(s) for s in split if s.startswith('<')]
    #return options, arguments
    return options

def printable_usage(doc):
    # in python < 2.7 you can't pass flags=re.IGNORECASE
    usage_split = re.split(r'([Uu][Ss][Aa][Gg][Ee]:)', doc)
    if len(usage_split) < 3:
        raise DocoptLanguageError('"usage:" (case-insensitive) not found.')
    if len(usage_split) > 3:
        raise DocoptLanguageError('More than one "usage:" (case-insensitive).')
    return re.split(r'\n\s*\n', ''.join(usage_split[1:]))[0].strip()

def formal_usage(printable_usage):
    pu = printable_usage.split()[1:]  # split and drop "usage:"
    return '( ' + ' '.join(') | (' if s == pu[0] else s for s in pu[1:]) + ' )'

def extras(help, version, options, doc):
    if help and any((o.name in ('-h', '--help')) and o.value for o in options):
        print(doc.strip("\n"))
        sys.exit()
    if version and any(o.name == '--version' and o.value for o in options):
        print(version)
        sys.exit()

class Dict(dict):
    def __repr__(self):
        return '{%s}' % ',\n '.join('%r: %r' % i for i in sorted(self.items()))

def docopt(doc, argv=None, help=True, version=None, options_first=False):
    """Parse `argv` based on command-line interface described in `doc`.

    `docopt` creates your command-line interface based on its
    description that you pass as `doc`. Such description can contain
    --options, <positional-argument>, commands, which could be
    [optional], (required), (mutually | exclusive) or repeated...

    Parameters
    ----------
    doc : str
        Description of your command-line interface.
    argv : list of str, optional
        Argument vector to be parsed. sys.argv[1:] is used if not
        provided.
    help : bool (default: True)
        Set to False to disable automatic help on -h or --help
        options.
    version : any object
        If passed, the object will be printed if --version is in
        `argv`.
    options_first : bool (default: False)
        Set to True to require options preceed positional arguments,
        i.e. to forbid options and positional arguments intermix.

    Returns
    -------
    args : dict
        A dictionary, where keys are names of command-line elements
        such as e.g. "--verbose" and "<path>", and values are the
        parsed values of those elements.

    Example
    -------
    >>> from docopt import docopt
    >>> doc = '''
    Usage:
        my_program tcp <host> <port> [--timeout=<seconds>]
        my_program serial <port> [--baud=<n>] [--timeout=<seconds>]
        my_program (-h | --help | --version)

    Options:
        -h, --help  Show this screen and exit.
        --baud=<n>  Baudrate [default: 9600]
    '''
    >>> argv = ['tcp', '127.0.0.1', '80', '--timeout', '30']
    >>> docopt(doc, argv)
    {'--baud': '9600',
     '--help': False,
     '--timeout': '30',
     '--version': False,
     '<host>': '127.0.0.1',
     '<port>': '80',
     'serial': False,
     'tcp': True}

    See also
    --------
    * For video introduction see http://docopt.org
    * Full documentation is available in README.rst as well as online
      at https://github.com/docopt/docopt#readme

    """
    if argv is None:
        argv = sys.argv[1:]
    DocoptExit.usage = printable_usage(doc)
    options = parse_defaults(doc)
    pattern = parse_pattern(formal_usage(DocoptExit.usage), options)
    # [default] syntax for argument is disabled
    #for a in pattern.flat(Argument):
    #    same_name = [d for d in arguments if d.name == a.name]
    #    if same_name:
    #        a.value = same_name[0].value
    argv = parse_argv(TokenStream(argv, DocoptExit), list(options),
                      options_first)
    pattern_options = set(pattern.flat(Option))
    for ao in pattern.flat(DocoptAnyOptions):
        doc_options = parse_defaults(doc)
        ao.children = list(set(doc_options) - pattern_options)
        #if any_options:
        #    ao.children += [Option(o.short, o.long, o.argcount)
        #                    for o in argv if type(o) is Option]
    extras(help, version, argv, doc)
    matched, left, collected = pattern.fix().match(argv)
    if matched and left == []:  # better error message if left?
        return Dict((a.name, a.value) for a in (pattern.flat() + collected))
    raise DocoptExit()

