from typing import List, Set, Optional, Tuple
import ast
import re

from cleanedit import CodeSpan

from .classify import is_import_span, is_main_guard_span

def extract_main_guard_span(spans: List[CodeSpan], omit_main: bool = False) -> Tuple[Optional[CodeSpan], List[CodeSpan]]:
    others = []
    main_guard = None
    for span in spans:
        if omit_main and is_main_guard_span(span):
            continue
        if re.search(r'if __name__\s*==\s*[\'\"]__main__[\'\"]', span.text):
            main_guard = span
        else:
            others.append(span)
    return main_guard, others

def extract_defined_names(span: CodeSpan) -> Set[str]:
    node = ast.parse(span.text)
    defs = set()
    for n in node.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            defs.add(n.name)
        elif isinstance(n, ast.Assign):
            for target in n.targets:
                if isinstance(target, ast.Name):
                    defs.add(target.id)
    return defs

builtins_names = [ x for x in __builtins__ if isinstance(x,object) ]

def extract_used_names(span: CodeSpan, trace: bool = False) -> Set[str]:
    node = ast.parse(span.text)
    used = set()
    class Visitor(ast.NodeVisitor):
        def visit_Name(self, n):
            if n.id not in builtins_names:
                if trace: print(f"Name : bespoke : id = {n.id}")
                used.add(n.id)
            else:
                if trace: print(f"Name : builtin : id = {n.id}")
        def visit_FunctionDef(self, n):
            if trace: print(f"Function ...")
            for deco in n.decorator_list:
                self.visit(deco)
            if n.returns:
                self.visit(n.returns)
        def visit_ClassDef(self, n):
            if trace: print(f"Class ...")
            for base in n.bases:
                self.visit(base)
            for deco in n.decorator_list:
                self.visit(deco)
        def visit_AnnAssign(self, n):
            if isinstance(n.annotation, ast.Name):
                name = n.annotation.id
                if name in builtins_names:
                    if trace: print(f"Annotation : builtin : name = {name}")
                    return
                else:
                    if trace: print(f"Annotation : bespoke : name = {name}")
            self.visit(n.annotation)
    Visitor().visit(node)
    return used
