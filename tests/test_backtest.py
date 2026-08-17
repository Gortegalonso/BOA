"""Puerta bloqueante de la Fase 3 (CLAUDE.md 10): recall 100% obligatorio
sobre el conjunto de verdad de 2018-2026. Si esto falla, no se puede pasar
a la Fase 4 (Colector B) sin ampliar el filtro primero.
"""

from boa_monitor.backtest import ejecutar
from boa_monitor.filtro import Cubo, evaluar_titulo


def test_recall_100_por_ciento_sobre_el_conjunto_de_verdad():
    resultado = ejecutar()
    assert resultado.faltantes == {}, f"Recall < 100%: faltan {resultado.faltantes}"
    assert resultado.recall == 1.0


def test_los_falsos_positivos_nunca_caen_en_el_cubo_seguro():
    # Los falsos positivos son aceptables (regla de diseño 1); que uno se
    # cuele en "seguro" en vez de "ambiguo" no lo es, porque cambia qué tan
    # rápido se revisa (alerta inmediata vs. resumen semanal), no si se revisa.
    resultado = ejecutar()
    for fecha_str, item, _reglas in resultado.sorpresas:
        cubo = evaluar_titulo(item.titulo).cubo
        assert cubo is Cubo.AMBIGUO, (
            f"Falso positivo en cubo '{cubo.value}' (se esperaba 'ambiguo') "
            f"el {fecha_str}: {item.titulo[:100]}"
        )
