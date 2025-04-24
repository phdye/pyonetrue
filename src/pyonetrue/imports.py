from typing import List, Tuple, Dict, DefaultDict
import ast
import sys
from collections import defaultdict
from cleanedit import CodeSpan

# Try to use stdlib_list if available, otherwise fallback to a static list
try:
    from stdlib_list import stdlib_list
    STDLIB_MODULES = set(stdlib_list(f"{sys.version_info.major}.{sys.version_info.minor}"))
except ImportError:
    STDLIB_MODULES = {
        "ast", "os", "sys", "re", "math", "itertools", "functools", "typing", "collections",
        "dataclasses", "hashlib", "pathlib", "argparse", "json", "time", "datetime",
        "subprocess", "threading", "multiprocessing", "unittest", "io", "shutil"
    }

def classify_import(module: str) -> str:
    if module.split(".")[0] in STDLIB_MODULES:
        return "stdlib"
    elif module in sys.builtin_module_names:
        return "stdlib"
    elif module.startswith("."):
        return "relative"
    else:
        return "thirdparty"

def normalize_import_spans(spans: List[CodeSpan], *, package_name: str = "cleanedit") -> List[CodeSpan]:
    """
    Normalize and group import spans:
    - Remove relative/self imports
    - Expand imports
    - Group by category
    - Sort within category
    - Consolidate "from x import y" into single lines
    - Use vertical form if the line would exceed 90 characters
    - Separate groups with blank lines
    """
    seen = set()
    grouped: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: {"import": [], "from": defaultdict(list)})

    for span in spans:
        try:
            parsed = ast.parse(span.text)
        except SyntaxError:
            continue

        for node in parsed.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name
                    line = f"import {mod}"
                    if line in seen or mod.startswith(package_name):
                        continue
                    seen.add(line)
                    category = classify_import(mod)
                    grouped[category]["import"].append(mod)

            elif isinstance(node, ast.ImportFrom):
                if node.level != 0 or not node.module or node.module.startswith(package_name):
                    continue
                for alias in node.names:
                    line = f"from {node.module} import {alias.name}"
                    if line in seen:
                        continue
                    seen.add(line)
                    category = classify_import(node.module)
                    grouped[category]["from"][node.module].append(alias.name)

    def emit_imports(imports: List[str], lineno: int) -> Tuple[List[CodeSpan], int]:
        spans = []
        for mod in sorted(set(imports)):
            line = f"import {mod}\n"
            spans.append(CodeSpan(
                kind="import",
                name=None,
                lineno=lineno,
                end_lineno=lineno,
                text=line,
                ast_node=None
            ))
            lineno += 1
        return spans, lineno

    def emit_from_imports(from_imports: Dict[str, List[str]], lineno: int) -> Tuple[List[CodeSpan], int]:
        spans = []
        for module in sorted(from_imports):
            names = sorted(set(from_imports[module]))
            inline = f"from {module} import {', '.join(names)}"
            if len(inline) > 90:
                body = ",\n".join(f"    {name}" for name in names)
                text = f"from {module} import (\n{body},\n)\n"
            else:
                text = inline + "\n"
            spans.append(CodeSpan(
                kind="importfrom",
                name=None,
                lineno=lineno,
                end_lineno=lineno + text.count("\n") - 1,
                text=text,
                ast_node=None
            ))
            lineno += text.count("\n")
        return spans, lineno

    result = []
    lineno = 1
    for group in ["stdlib", "thirdparty", "local"]:
        entries = grouped.get(group)
        if not entries:
            continue
        imps, lineno = emit_imports(entries["import"], lineno)
        frs, lineno = emit_from_imports(entries["from"], lineno)
        result.extend(imps + frs)
        result.append(CodeSpan(
            kind="blank",
            name=None,
            lineno=lineno,
            end_lineno=lineno,
            text="\n",
            ast_node=None
        ))
        lineno += 1

    return result
