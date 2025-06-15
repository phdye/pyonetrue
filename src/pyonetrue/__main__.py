"""Package entry point when executing `python -m pyonetrue`.

Runs the main CLI function to flatten the specified package or file.
"""

import sys
from .cli import main

if __name__ == "__main__":
    exit(main(sys.argv))