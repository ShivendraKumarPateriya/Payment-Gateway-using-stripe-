"""Compatibility entrypoint for running the FastAPI app.

This file keeps the original `backend.main:app` import path working,
while the real application code lives inside the structured `backend/app`
package.
"""

try:
    # Works when server is started from project root:
    # `uvicorn backend.main:app --reload`
    from backend.app.main import app
except ModuleNotFoundError:
    # Works when server is started from inside `backend/`:
    # `uvicorn main:app --reload`
    import os
    import sys

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)

    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from backend.app.main import app

__all__ = ["app"]
