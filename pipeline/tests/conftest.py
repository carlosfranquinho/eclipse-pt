"""Fixtures partilhadas pelos testes do pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

CANON = RAIZ / "cache" / "canon" / "canon.json"


@pytest.fixture(scope="session")
def canon() -> list[dict]:
    """Todos os eclipses do canon no intervalo do projeto."""
    if not CANON.exists():
        pytest.skip("cache do canon em falta, correr ingest_canon.py")
    return json.loads(CANON.read_text())["eclipses"]


@pytest.fixture(scope="session")
def por_data(canon: list[dict]) -> dict[str, dict]:
    """Eclipses indexados por data gregoriana, no formato AAAA-MM-DD."""
    return {f"{e['ano']:04d}-{e['mes']:02d}-{e['dia']:02d}": e for e in canon}
