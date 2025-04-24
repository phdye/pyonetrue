def is_classdef_span(span) -> bool:
    return span.kind == "classdef"

def is_functiondef_span(span) -> bool:
    return span.kind == "functiondef"

def is_main_guard_span(span) -> bool:
    return span.kind == "if" and "__name__" in span.text and "__main__" in span.text

def is_import_span(span) -> bool:
    return span.kind in {"import", "importfrom"}
