from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from app.api.routes import router


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

from app.database.oracle import test_connection  # noqa: E402


app = FastAPI(title="ERR2TEXT API", version="0.1.0")
app.include_router(router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/oracle")
def oracle_health() -> dict[str, object]:
    try:
        return test_connection()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"ok": False, "database": "oracle", "error": type(exc).__name__},
        ) from exc
