#!/usr/bin/env python3
import astfrom collections import defaultdictfrom dataclasses import dataclass, fieldimport importlib.utilfrom pathlib import Pathimport reimport sysfrom typing import List, Optional, Tuple, Union
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
# normailize_imports :
    "normalize_imports",
    "format_plain_import",
    "format_from_import",
    "is_stdlib_module",
    "set_line_length",
    "get_line_length",
    "ImportEntry",
]

r"""
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
at the end of without reordering unless the --no-cli option is used.  Other
__main__.py modules are not included by default.  If you want to include
one of them instead, you can use the --main-from option to specify the
sub-package from which to include __main__.py.

Default behavior is to :
* All relative imports are eliminated. Flattened output is fully self-contained.
* Main guards are discarded, but this can be changed with the --main-all
  or --main-from options.
* Write the output to stdout, but this can be changed with the --output
* Name clashes, duplicate top-level names, are not allowed by default.
* If `__main__.py` is being included, prepend shebang.

Options:
  -s, --shebang <shebang>  Prepend <sheband> if `__main__.py` is being appended.  [default: #!/usr/bin/env python3]
  -o, --output <file>      Write output to file (default: stdout).
  --no-cli                 Do not include package's __main__.py.
  -m, --main-from <mod>    Include __main__.py from the specified sub-package.
                           Only one __main__.py module is allowed.
                           Incompatible with --no-cli.
  -a, --all-guards         Include all __main__ guards. (default: discard)
  -g, --guards-from <mod>  Include __main__ guards only from <mod>.
  -e, --exclude <exclude>  Exclude specified packages or modules, comma separated.
  -i, --include <include>  Exclude specified packages or modules, comma separated.
  --ignore-clashes         Allow duplicate top-level names without error.
  -h, --help               Show this help message.
  --version                Show version.
  --show-cli-args          Show the command line arguments that would be passed to the
                           CLI and exit.  This is useful for debugging.
"""

__version__ = "0.5.4"

def main(argv=sys.argv):
    """Main function to run the CLI tool."""

    args = docopt(__doc__, argv=argv[1:], version=__version__)
    if args['--no-cli'] and args['--main-from']:
        raise ValueError("Invalid options: cannot specify both --no-cli and --main-from")

    ctx = FlatteningContext(
        package_path=args['<input>'],
        output=args.get('--output') or 'stdout',
        no_cli=bool(args.get('--no-cli')),
        main_from=args.get('--main-from', '').split(',') if args.get('--main-from') else [],
        guards_all=bool(args.get('--all-guards')),
        guards_from=args.get('--guards-from', '').split(',') if args.get('--guards-from') else [],
        ignore_clashes=bool(args.get('--ignore-clashes')),
        exclude=args.get('--exclude', '').split(',') if args.get('--exclude') else [],
        include=args.get('--include', '').split(',') if args.get('--include') else [],
        shebang=args.get('--shebang', '#!/usr/bin/env python3'),
    )

    ctx.main_from = ctx.main_from[0] if ctx.main_from else None
    if ctx.main_from:
        ctx.no_cli = False
    elif not ctx.no_cli:
        ctx.main_from = '__main__' # primary package
    if args['--show-cli-args']:
        print(f"CLI args:\n{ctx}")
        return 0

    ctx.discover_modules()
    ctx.gather_main_guard_spans()
    spans = ctx.get_final_output_spans()

    lines = []
    if ctx.shebang:
        lines.append(ctx.shebang.rstrip("\n") + "\n")
    lines.extend(span.text for span in spans)
    text = "".join(lines)

    if ctx.output == "stdout":
        sys.stdout.write(text)
    else:
        Path(ctx.output).write_text(text)

    return 0

class Span:
    """
    Represents a top-level code segment.
    """
    def __init__(self, text: str, kind: str):
        self.text = text
        self.kind = kind  # 'import', 'class', 'function', 'logic', 'main_guard'

    def __repr__(self):
        return f"Span(kind={self.kind!r}, text={self.text!r})"

def extract_spans(source: Union[str, Path], filename: str = '<unknown>') -> List[Span]:
    """
    Parse the source using ast.parse and extract top-level spans in order.
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

        # Extract source text for the node
        # text = ast.get_source_segment(source, node)
        # if text is None:
        #     # Fallback: use generic node representation
        #     text = ast.unparse(node) if hasattr(ast, 'unparse') else ''

        # Extract the text from the lines -- required to capture decorators
        spans.append(Span(''.join(lines[start:end]), kind))

    return spans

DEBUG = False

@dataclass
class FlatteningContext:

    package_path       : Union[Path, str]
    package_name       : str                           = ""
    main_py            : tuple[str, list[Span]]        = (None, [])
    module_spans       : list[tuple[str, list[Span]]]  = field(default_factory=list)
    guard_sources      : dict[str, list[Span]]         = field(default_factory=dict)

    # Discovery -- inclusion/exclusion
    no_cli             : bool                          = False
    main_from          : list[str]                     = field(default_factory=list)
    exclude            : list[str]                     = field(default_factory=list)
    include            : list[str]                     = field(default_factory=list)

    # Conflict detection
    ignore_clashes     : bool                          = False

    # Output generation
    output             : str                           = "stdout"
    shebang            : str                           = "#!/usr/bin/env python3"
    guards_all         : bool                          = False
    guards_from        : list[str]                     = field(default_factory=list)

    def __post_init__(self):
        if not self.package_path:
            raise ValueError("package 'package_path' cannot be empty (None, '', etc.)")
        # Resolve package_path to file, dir, or package name
        path = Path(self.package_path)
        if DEBUG: print(f"DEBUG: Resolved path = {path}", file=sys.stderr)
        if path.exists():
            if path.is_dir():
                self.package_name = path.name
            elif path.is_file():
                self.package_name = path.stem
            else:
                raise ValueError(f"input path '{self.package_path}' exists but is neither a file nor a directory")
        else:
            if DEBUG: print("DEBUG: package_path not   found as file/dir, trying as package name", file=sys.stderr)
            spec = importlib.util.find_spec(self.package_path)
            if spec and spec.submodule_search_locations:
                path = Path(spec.submodule_search_locations[0])
                self.package_name = path.name
            else:
                raise ValueError(f"Cannot infer project package name from {self.package_path!r}")

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
            raise ValueError("Cannot specify `include` without `exclude`")

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
            raise ValueError("module 'path' cannot be empty (None, '', etc.)")
        if isinstance(obj, FlatteningModule):
            fm = obj
        elif isinstance(obj, (Path, str)):
            fm = FlatteningModule(self, Path(obj))
        else:
            raise ValueError(f"Invalid module path: {obj} -- must be str, Path, or FlatteningModule")

        if DEBUG: print(f"\nDEBUG: Adding module {fm.module = } from {fm.path = }", file=sys.stderr)

        spans = extract_spans(fm.path)
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
        if self.no_cli:
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
                    continue  # no_cli active, skip all __main__.py
                if allowed_main and full_mod != allowed_main:
                    if DEBUG: print(f"DEBUG: Discover - wrong cli - skipping module {full_mod = }, from {subpath = }", file=sys.stderr)
                    continue  # only allow exactly the requested __main__.py
                self.main_py = full_mod

            self.add_module(subpath)

    def gather_root_spans(self):
        retained_all = None
        retained_imports = []
        retained_logic = []

        for mod, spans in self.module_spans:
            if mod == self.package_name:
                for s in spans:
                    if s.kind == "__all__":
                        retained_all = s
                    elif s.kind == "import":
                        retained_imports.append(s)
                    elif s.kind == "main_guard":
                        pass
                    else:
                        retained_logic.append(s)
        return retained_all, retained_imports, retained_logic

    def gather_module_spans(self):
        non_root_spans = []

        for mod, spans in self.module_spans:
            if mod == self.package_name:
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
        return main_spans if (main_mod and main_spans and not self.no_cli) else []

    def normalize_and_assemble(self, imports, all_decl, logic, guards, main):
        # Normalize imports
        imports, import_symbols = normalize_imports(
            package_name=self.package_name,
            import_spans=imports,
        )

        ordered = list(imports)

        blank_line = Span(kind="blank", text="\n")

        if all_decl:
            ordered.append(blank_line)
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
                        raise Exception(f"Duplicate top-level name detected: {name}")
                    seen.add(name)

    def get_final_output_spans(self):
        all_decl, root_imports, root_logic = self.gather_root_spans()
        module_spans = self.gather_module_spans()
        main_guards = self.gather_main_guard_spans()
        main_body = self.get_main_spans()

        imports = root_imports + [s for s in module_spans if s.kind == "import"]
        logic = root_logic + [s for s in module_spans if s.kind not in["import", "main_guard"]]

        spans, import_symbols = self.normalize_and_assemble(
            imports, all_decl, logic, main_guards, main_body
        )

        self.check_clashes(spans, import_symbols)
        return spans

class FlatteningModule:

    __slots__ = ("module", "path")

    def __init__(self, ctx : FlatteningContext, path: Path):
        if not path.is_file():
            raise ValueError(f"FlatteningModule must be created from a file: {path}")

        try:
            relpath = path.relative_to(ctx.package_path)
        except ValueError:
            raise ValueError(f"Path {path} is not inside package root {ctx.package_path}")

        if relpath == Path('.'):
            relpath = Path(ctx.package_path.name)
        if relpath.name == "__init__.py":
            self.module = ctx.package_name
        else:
            mod_suffix = str(relpath.with_suffix('')).replace('/', '.')
            self.module = ctx.package_name + "." + mod_suffix

        self.path = path

def dotted_member_of(dotted: str, module_list: list[str]) -> bool:
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

def normalize_a_module_name(mod: str, package_name: str) -> str:
    if mod.startswith(package_name + ".") or mod == package_name:
        return mod
    else:
        return package_name + "." + mod.lstrip('.')

def normalize_module_names(
    package_name: str,
    module_names: Union[str, list[str]]
) -> list[str]:
    if isinstance(module_names, str):
        module_names = [normalize_a_module_name(module_names, package_name)]
    if not isinstance(module_names, list):
        raise ValueError(f"module_names must be str or list of str, not {type(module_names)}")
    return [normalize_a_module_name(mod, package_name) for mod in module_names]

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
            raise ValueError(f"Name clash detected: {name} in module {entry.module}, already imported from {names[name]}")
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
                lines = format_plain_import(plain_entries)
                output_spans.extend([Span(kind="import", text=line) for line in sorted(lines)])
            if from_entries:
                lines = format_from_import(from_entries)
                output_spans.extend([Span(kind="import", text=line) for line in sorted(lines)])
        output_spans.append(Span(kind="blank", text="\n"))

    return output_spans, imported_names

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

def set_line_length(length: int):
    """
    Set the line length for formatting imports.
    """
    global LINE_LENGTH
    if length > 0:
        LINE_LENGTH = length
    else:
        raise ValueError("Line length must be a positive integer.")

def get_line_length() -> int:
    """
    Get the current line length for formatting imports.
    """
    return LINE_LENGTH

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
            elif AnyOptions in types:
                optional = [c for c in children if type(c) is AnyOptions][0]
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

class AnyOptions(DocoptOptional):

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
        return [AnyOptions()]
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
    for ao in pattern.flat(AnyOptions):
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

