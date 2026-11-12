"""Compatibility entry point for the ORDS-backed MVP3 worker.

The implementation lives in :mod:`ords_worker`.  This file remains because
existing container definitions invoke ``python backend/worker.py``.  There is
deliberately no local queue implementation or fallback here.
"""

from ords_worker import main


if __name__ == "__main__":
    raise SystemExit(main())
