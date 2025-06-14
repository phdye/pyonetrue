"""Vendored pathlib module.

This module simply re-exports everything from the standard library
``pathlib`` package.  It exists so that the rest of the project can
consistently import :class:`Path` and related helpers from
``pyonetrue.vendor.pathlib`` instead of relying directly on the
interpreter's implementation.
"""

import pathlib as _stdlib_pathlib
from pathlib import *  # noqa: F401,F403

__all__ = getattr(_stdlib_pathlib, "__all__", [n for n in globals() if not n.startswith("_")])
