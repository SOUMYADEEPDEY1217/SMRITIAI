"""
App entrypoint (`uvicorn main:app`, as documented in the README).

BUGFIX: this used to be a second, hand-maintained copy of app/main.py with
its own CORS/middleware/router setup that had drifted out of sync with the
real one (e.g. missing OPTIONS in allow_methods, different version string).
Two copies of "the app" is exactly how these two things stop agreeing with
each other. Now there is one definition (app/main.py) and this file just
re-exports it, so `uvicorn main:app` and `uvicorn app.main:app` are always
identical.
"""
from app.main import app

__all__ = ["app"]
