"""Caché local del RSS crudo y registro de documentos ya vistos.

La caché de crudos cubre dos necesidades a la vez: el requisito de 7.1
("caché local de todo lo descargado") y la base para los fixtures de
regresión de 9.2. El registro de "vistos" evita re-alertar sobre el mismo
DOCN en cada ejecución horaria dentro del mismo día.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
DIR_DATOS = RAIZ_PROYECTO / "data"
DIR_CACHE_RSS = DIR_DATOS / "cache_rss"
FICHERO_VISTOS = DIR_DATOS / "vistos.json"


def ruta_cache_rss(fecha: date) -> Path:
    return DIR_CACHE_RSS / f"{fecha.isoformat()}.rss"


def guardar_raw(fecha: date, contenido: bytes) -> Path:
    DIR_CACHE_RSS.mkdir(parents=True, exist_ok=True)
    ruta = ruta_cache_rss(fecha)
    ruta.write_bytes(contenido)
    return ruta


def cargar_raw(fecha: date) -> bytes | None:
    ruta = ruta_cache_rss(fecha)
    if not ruta.exists():
        return None
    return ruta.read_bytes()


def cargar_vistos() -> set[str]:
    if not FICHERO_VISTOS.exists():
        return set()
    return set(json.loads(FICHERO_VISTOS.read_text(encoding="utf-8")))


def guardar_vistos(docns: set[str]) -> None:
    DIR_DATOS.mkdir(parents=True, exist_ok=True)
    FICHERO_VISTOS.write_text(
        json.dumps(sorted(docns), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def marcar_vistos(nuevos: set[str]) -> set[str]:
    vistos = cargar_vistos()
    vistos |= nuevos
    guardar_vistos(vistos)
    return vistos
