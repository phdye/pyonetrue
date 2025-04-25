from .extract_ast import extract_spans, Span

from .flattening import (
        FlatteningContext,
        FlatteningModule,
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

from .package import (
    build_flattening_context,
    populate_flattening_context,
    generate_flattened_spans,
    write_flattened_output,
    run_cli_logic,
    CliOptions,
)

from .cli import __version__, main

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
# normailize_imports :
    "normalize_imports",
    "format_plain_import",
    "format_from_import",
    "is_stdlib_module",
    "set_line_length",
    "get_line_length",
    "ImportEntry",
# package
    "build_flattening_context",
    "populate_flattening_context",
    "generate_flattened_spans",
    "write_flattened_output",
    "run_cli_logic",
    "CliOptions",
]
