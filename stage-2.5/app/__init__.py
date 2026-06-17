"""Stage 2.5 wrapper package.

This package exists so the directory has an __init__.py. The actual
FastAPI app is in `app/wrap.py` and is launched from the stage-2.5 root
as `python -m app.wrap`.

Note: stage-2.5's modules are imported as `from app.wrap import create_app`,
which means `app` here is stage-2.5's package. The wrap module reaches
into stage-3's modules via a virtual `stage3_app` package (see app/wrap.py).
"""
from __future__ import annotations

__version__ = "0.2.5.0"
