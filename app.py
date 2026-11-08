"""Root entrypoint to allow running `uvicorn app:app` or `python app.py` from the project root.
Delegates cleanly to `backend.app:app`.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_BACKEND = _ROOT / "backend"
for _p in (str(_ROOT), str(_BACKEND)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.app import app  # noqa: E402, F401

if __name__ == "__main__":
    import uvicorn
    print("\n⚡ Starting PS1 Valuation Engine on http://localhost:8000 ...\n")
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
