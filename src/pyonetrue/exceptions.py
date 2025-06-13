"""Custom exceptions for the pyonetrue flattening tool."""

"""
Custom exceptions for pyonetrue, each representing a single, specific error scenario.
"""

class PyonetrueError(Exception):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Base exception for all pyonetrue errors."""
    pass

class CLIOptionError(PyonetrueError):
    """Raised when invalid or incompatible command-line options are provided to the CLI.

    Use this exception to signal errors such as specifying mutually exclusive flags
    (e.g., `--no-cli` and `--main-from`).
    """
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Invalid combination or value of CLI options."""
    pass

class DuplicateNameError(PyonetrueError):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Detected duplicate top-level symbol names."""
    pass

class ImportNormalizationError(PyonetrueError):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Errors during import deduplication and normalization processes."""
    pass

class IncludeExcludeError(PyonetrueError):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Invalid usage of include/exclude flags."""
    pass

class FlatteningError(PyonetrueError):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """General errors occurring in the flattening pipeline."""
    pass

class ModuleInferenceError(PyonetrueError):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Cannot infer package or module name from the given path."""
    pass

class PathError(PyonetrueError):
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """TODO: Expand this docstring."""
    """Errors related to filesystem paths or module resolution."""
    pass