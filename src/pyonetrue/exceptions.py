"""
Custom exceptions for pyonetrue, each representing a single, specific error scenario.
"""

class PyonetrueError(Exception):
    """Base exception for all pyonetrue errors."""
    pass

class CLIOptionError(PyonetrueError):
    """Invalid combination or value of CLI options."""
    pass

class DuplicateNameError(PyonetrueError):
    """Detected duplicate top-level symbol names."""
    pass

class ImportNormalizationError(PyonetrueError):
    """Errors during import deduplication and normalization processes."""
    pass

class IncludeExcludeError(PyonetrueError):
    """Invalid usage of include/exclude flags."""
    pass

class FlatteningError(PyonetrueError):
    """General errors occurring in the flattening pipeline."""
    pass

class ModuleInferenceError(PyonetrueError):
    """Cannot infer package or module name from the given path."""
    pass

class PathError(PyonetrueError):
    """Errors related to filesystem paths or module resolution."""
    pass

