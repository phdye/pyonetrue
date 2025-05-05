import ast
import sys
from collections import defaultdict
from typing import List, Tuple
from dataclasses import dataclass

from .extract_ast import Span

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

# Default line length for formatting imports
DEFAULT_LINE_LENGTH = 80

# Set the line length for formatting imports
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
                text = "\n".join(format_plain_import(plain_entries)) + '\n'
                output_spans.append(Span(kind="import", text=text))
            if from_entries:
                text = "\n".join(format_from_import(from_entries)) + '\n'
                output_spans.append(Span(kind="import", text=text))
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

# User configurable line length
def set_line_length(length: int):
    """
    Set the line length for formatting imports.
    """
    global LINE_LENGTH
    if length > 0:
        LINE_LENGTH = length
    else:
        raise ValueError("Line length must be a positive integer.")

# Get the current line length
def get_line_length() -> int:
    """
    Get the current line length for formatting imports.
    """
    return LINE_LENGTH
