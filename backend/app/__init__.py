import sys
from pathlib import Path

_this_dir = Path(__file__).resolve().parent
_backend_dir = _this_dir.parent
_repo_root = _backend_dir.parent

if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
