"""Prueba de regresión (CLAUDE.md 9.2): sobre fixtures de días con positivo
conocido, el filtro debe seguir marcando ese DOCN como "seguro" tras
cualquier cambio en el código. Objetivo: recall 100%, nunca se reduce.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from boa_monitor.filtro import Cubo, evaluar_titulo
from boa_monitor.rss import parsear_rss

DIR_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "regresion"
POSITIVOS = json.loads((DIR_FIXTURES / "positivos_esperados.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("fecha_str", sorted(POSITIVOS))
def test_recall_sobre_fixture_historico(fecha_str):
    fecha = date.fromisoformat(fecha_str)
    contenido = (DIR_FIXTURES / f"{fecha_str}.rss").read_bytes()
    items = parsear_rss(contenido, fecha)

    docns_marcados_seguro = {
        item.docn for item in items if evaluar_titulo(item.titulo).cubo is Cubo.SEGURO
    }

    esperados = set(POSITIVOS[fecha_str]["docn_esperados"])
    faltantes = esperados - docns_marcados_seguro
    assert not faltantes, (
        f"Falso negativo en {fecha_str}: el filtro no marcó {faltantes} "
        f"(orden {POSITIVOS[fecha_str]['orden']})"
    )
