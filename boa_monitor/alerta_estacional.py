"""Alerta estacional (CLAUDE.md 9.4): si llega el 10 de septiembre sin
convocatoria detectada este año, avisar. La ausencia de señal es señal.
"""

from __future__ import annotations

import json
import sys
from datetime import date

from boa_monitor.cache import DIR_DATOS

FICHERO_CONVOCATORIAS = DIR_DATOS / "convocatorias.json"
FECHA_LIMITE = (9, 10)  # (mes, día)


def hay_convocatoria_detectada_este_anio(hoy: date) -> bool:
    if not FICHERO_CONVOCATORIAS.exists():
        return False
    registros = json.loads(FICHERO_CONVOCATORIAS.read_text(encoding="utf-8"))

    ventana_inicio = date(hoy.year, 7, 1)
    ventana_fin = date(hoy.year, 9, 30)
    return any(
        ventana_inicio <= date.fromisoformat(r["fecha_boa"]) <= ventana_fin
        and r.get("cubo") == "seguro"
        for r in registros
    )


def verificar(hoy: date | None = None) -> bool:
    """Devuelve True si todo va bien (o aún no toca comprobar)."""
    hoy = hoy or date.today()
    if (hoy.month, hoy.day) < FECHA_LIMITE:
        return True
    return hay_convocatoria_detectada_este_anio(hoy)


if __name__ == "__main__":
    if verificar():
        print("OK: convocatoria detectada dentro de la ventana crítica de este año, o aún no toca comprobar.")
        sys.exit(0)
    print(
        "ALERTA: no he detectado ninguna convocatoria POT este año. "
        "Revísalo a mano en https://www.boa.aragon.es/"
    )
    sys.exit(1)
