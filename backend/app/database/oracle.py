from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import oracledb


def _enabled() -> bool:
    return os.getenv("ORACLE_ENABLED", "no").strip().lower() in {"1", "true", "yes", "on"}


def _connection_kwargs() -> dict[str, str]:
    user = os.getenv("ORACLE_USER", "").strip()
    password = os.getenv("ORACLE_PASSWORD", "")
    dsn = os.getenv("ORACLE_DSN", "").strip()
    if not user or not password or not dsn:
        raise RuntimeError("ORACLE_USER, ORACLE_PASSWORD and ORACLE_DSN are required")

    kwargs: dict[str, str] = {"user": user, "password": password, "dsn": dsn}
    config_dir = os.path.expanduser(os.getenv("ORACLE_CONFIG_DIR", "").strip())
    wallet_location = os.path.expanduser(os.getenv("ORACLE_WALLET_LOCATION", "").strip())
    wallet_password = os.getenv("ORACLE_WALLET_PASSWORD", "")
    if config_dir:
        kwargs["config_dir"] = config_dir
    if wallet_location:
        kwargs["wallet_location"] = wallet_location
    if wallet_password:
        kwargs["wallet_password"] = wallet_password
    return kwargs


@contextmanager
def connection() -> Iterator[oracledb.Connection]:
    """Open one Oracle connection using this project's environment only."""
    if not _enabled():
        raise RuntimeError("Oracle backend is disabled (ORACLE_ENABLED is not enabled)")
    with oracledb.connect(**_connection_kwargs()) as conn:
        yield conn


def test_connection() -> dict[str, object]:
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("select 1 from dual")
            value = cursor.fetchone()[0]
    return {"ok": value == 1, "database": "oracle", "probe": value}
