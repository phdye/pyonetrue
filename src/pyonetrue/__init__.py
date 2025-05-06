from .extract_ast import extract_spans, Span

from .flattening import (
    FlatteningContext,
    FlatteningModule,
    normalize_a_module_name,
    normalize_module_names,
)

from .normalize_imports import (
    normalize_imports,
    format_plain_import,
    format_from_import,
    is_stdlib_module,
    set_line_length,
    get_line_length,
    ImportEntry,
)

from .cli import __version__, main

from .exceptions import (
    PyonetrueError,
    CLIOptionError,
    DuplicateNameError,
    ImportNormalizationError,
    IncludeExcludeError,
    FlatteningError,
    ModuleInferenceError,
    PathError,
)

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
    "normalize_a_module_name",
    "normalize_module_names",
# normailize_imports :
    "normalize_imports",
    "format_plain_import",
    "format_from_import",
    "is_stdlib_module",
    "set_line_length",
    "get_line_length",
    "ImportEntry",
# exceptions
    "PyonetrueError",
    "CLIOptionError",
    "DuplicateNameError",
    "ImportNormalizationError",
    "IncludeExcludeError",
    "FlatteningError",
    "ModuleInferenceError",
    "PathError",
]
