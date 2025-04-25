import ast
from typing import List, Tuple, Optional, Union
from pathlib import Path

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
