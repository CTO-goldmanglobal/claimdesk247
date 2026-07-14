# Vercel Python serverless entrypoint for the ClaimDesk 247 engine.
# Vercel exposes a module-level ASGI `app` from /api/*.py as a function.
#
# Deploy layout: Vercel "Root Directory" = `.` (monorepo root). The repo root
# contains `api/`, `requirements.txt`, `vercel.json`, plus the engine's
# `stage-2.5/`, `stage-3/`, `stage-4/` directories as siblings of `api/`.
#
# Loading stage-2.5/app/wrap.py as the package `app.wrap` keeps wrap.py's
# `from . import __version__` working.
#
# VERIFY LOCALLY before trusting in prod:
#   pip install -r requirements.txt
#   (cd stage-2.5 && python3 tests/run_acceptance.py)      # 18 + regression
#   uvicorn api.index:app --reload                          # smoke /healthz
import pathlib
import sys

# __file__ = <monorepo>/api/index.py
# parent = api/, parent.parent = monorepo root
_MONOREPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
# stage-2.5 first so `app` resolves to the wrapper package (not stage-3's).
sys.path.insert(0, str(_MONOREPO_ROOT / "stage-2.5"))
# Also add the monorepo root so stage-3/stage-4 absolute imports resolve.
sys.path.insert(0, str(_MONOREPO_ROOT))

from app.wrap import app  # noqa: E402  (FastAPI instance)

__all__ = ["app"]
