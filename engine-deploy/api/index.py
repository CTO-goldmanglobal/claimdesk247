# Vercel Python serverless entrypoint for the ClaimDesk 247 engine.
# Vercel exposes a module-level ASGI `app` from /api/*.py as a function.
#
# The deploy ROOT must contain stage-2.5/, stage-3/, stage-4/ as siblings of
# this api/ folder (wrap.py bootstraps stage-3 by relative path, and the Stage 4
# Supabase adapter lives in stage-4/app/). Loading stage-2.5/app/wrap.py as the
# package `app.wrap` keeps wrap.py's `from . import __version__` working.
#
# VERIFY LOCALLY before trusting in prod (cannot be run from the planning seat):
#   pip install -r requirements.txt
#   (cd stage-2.5 && python3 tests/run_acceptance.py)      # 18 + regression
#   uvicorn api.index:app --reload                          # smoke /healthz
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
# stage-2.5 first so `app` resolves to the wrapper package (not stage-3's).
sys.path.insert(0, str(_ROOT / "stage-2.5"))

from app.wrap import app  # noqa: E402  (FastAPI instance)

__all__ = ["app"]
