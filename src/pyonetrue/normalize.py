import sys
from typing import List

from cleanedit import CodeSpan

from .classify import is_import_span


def normalize_import_spans(spans: List[CodeSpan], trace: bool = False) -> List[CodeSpan]:
    filtered = []
    for s in spans:
        if not is_import_span(s):
            continue 
        if s.kind == "importfrom":
            package = s.text.strip().split()[1]
            if package.startswith("."):
                if trace: print(f"[TRACE] Removing relative import: {s.text.strip()}", file=sys.stderr)
                continue
            if trace: print(f"[TRACE] SPAN kind={s.kind} text={s.text.strip()!r}", file=sys.stderr)
        filtered.append(s)

    unique_texts = sorted(set(s.text for s in filtered))
    lines = [line for block in unique_texts for line in block.splitlines(keepends=True)]
    joined = ''.join(lines)
    return [CodeSpan(
        kind="import",
        name=None,
        lineno=1,
        end_lineno=len(lines),
        text=joined
    )]

