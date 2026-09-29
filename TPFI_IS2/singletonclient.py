"""Executable wrapper script for SingletonClient CLI."""

import sys
from pathlib import Path

# Ensure src directory is in Python path for direct script execution
src_path = Path(__file__).resolve().parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from tpfi_is2.singleton_client import main

if __name__ == "__main__":
    main()
