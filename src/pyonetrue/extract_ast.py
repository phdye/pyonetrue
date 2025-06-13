"""Parsing Python source and extract top-level code spans."""

import ast
from typing import List, Union
from pathlib import Path

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
