"""Executable CLI wrapper for ObserverClient at project root.

Format: python observerclient.py {-s=hostname} {-p=port} {-o=output.json}{-v}
"""

import sys
from pathlib import Path

_src = Path(__file__).resolve().parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from tpfi_is2.observer_client import main  # noqa: E402

if __name__ == "__main__":
    main()
