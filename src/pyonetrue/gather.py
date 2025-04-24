import ast
from typing import List, Set, Optional, Tuple

from cleanedit import CodeSpan

from .classify import is_import_span, is_main_guard_span

def gather_imported_names(spans: List[CodeSpan]) -> Set[str]:
    """Collect all names introduced by top-level imports."""
    imported = set()
    for s in spans:
        if s.kind == "import":
            # e.g. "import sys, re as R"
            # parse out introduced names
            # naive approach: split on commas, etc.
            # We'll do a quick parse with ast.
            try:
                mod = ast.parse(s.text)
                for node in mod.body:
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported.add(alias.asname or alias.name.split(".")[0])
            except SyntaxError:
                pass
        elif s.kind == "importfrom":
            # e.g. "from typing import List, Dict"
            try:
                mod = ast.parse(s.text)
                for node in mod.body:
                    if isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            imported.add(alias.asname or alias.name)
            except SyntaxError:
                pass
    return imported

def gather_class_and_func_names(spans: List[CodeSpan]) -> Set[str]:
    """Collect all classdef or functiondef names from top-level AST nodes."""
    declared = set()
    for s in spans:
        if s.kind in ("classdef", "functiondef"):
            # parse s.text
            try:
                mod = ast.parse(s.text)
                for node in mod.body:
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                        declared.add(node.name)
            except SyntaxError:
                pass
    return declared

