from typing import List
import sys

from cleanedit import CodeSpan

from .gather import gather_imported_names, gather_class_and_func_names
from .extract import extract_used_names, extract_defined_names
from .classify import is_import_span, is_main_guard_span, is_functiondef_span, is_classdef_span
from .imports import normalize_import_spans

def reorder_top_level_spans(package: str, spans: List[CodeSpan], *, omit_main: bool = False, trace: bool = False) -> List[CodeSpan]:
    """
    Reorders top-level spans into a normalized form:
    - __future__ imports first (in original order)
    - then other imports (sorted by lineno)
    - then class definitions
    - then function definitions
    - then any remaining top-level code
    - optionally omit the main guard span
    - main guard span (if any) is always moved to the end
    """
    future_imports = []
    regular_imports = []
    class_spans = []
    func_spans = []
    main_spans = []
    other_spans = []

    trace = False;
    if trace: print(f"Reordering {len(spans)} spans", file=sys.stderr)

    for span in spans:
        if is_import_span(span):
            if "__future__" in span.text:
                future_imports.append(span)
                if trace: print(f"[FUTURE]\n{span.text}", file=sys.stderr)
            else:
                regular_imports.append(span)
                if trace: print(f"[IMPORT]\n{span.text}", file=sys.stderr)
        elif is_classdef_span(span):
            class_spans.append(span)
            if trace: print(f"[CLASS]\n{span.text}", file=sys.stderr)
        elif is_functiondef_span(span):
            func_spans.append(span)
            if trace: print(f"[FUNC]\n{span.text}", file=sys.stderr)
        elif is_main_guard_span(span):
            if not omit_main:
                main_spans.append(span)
                if trace: print(f"[MAIN]\n{span.text} (included)", file=sys.stderr)
            else:
                if trace: print(f"[MAIN]\n{span.text} (omitted)", file=sys.stderr)
        else:
            other_spans.append(span)
            if trace: print(f"[OTHER]\n{span.text}", file=sys.stderr)

    if False:
        print("[IMPORTS]\n")
        for span in future_imports + regular_imports:
            print(f"{span.text}\n", file=sys.stderr)
        print("[CLASSES]\n")
        for span in class_spans:
            print(f"{span.text}\n", file=sys.stderr)
        print("[FUNCTIONS]\n")
        for span in func_spans:
            print(f"{span.text}\n", file=sys.stderr)
        print("[OTHER]\n")
        for span in other_spans:
            # skip comments, docstrings, and empty lines
            if span.kind == "comment" or span.kind == "blank" or span.kind == "str":
                continue
            print(f"{span.text}\n", file=sys.stderr)
        print("[MAIN]\n")
        for span in main_spans:
            print(f"{span.text}\n", file=sys.stderr)

    imports = normalize_import_spans(regular_imports, package_name=package)

    # Preserve original order for __future__ imports
    import_block = future_imports + imports
    return (import_block, class_spans + func_spans + other_spans + main_spans)
