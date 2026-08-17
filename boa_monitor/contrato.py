"""Prueba de contrato (CLAUDE.md 9.3): ¿la fuente sigue igual?

Descarga en vivo el RSS de una fecha pasada conocida (la convocatoria 2026,
ya publicada) y comprueba que el feed sigue teniendo la forma documentada:
mismo número de documentos, misma codificación, los tres campos por item y
el documento de la convocatoria en su posición conocida. Un fallo aquí
significa que el BOA cambió algo, no que el código esté roto (eso es 9.2).
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from datetime import date

from boa_monitor.rss import construir_url, descargar_rss

FECHA_CONOCIDA = date(2026, 8, 6)
DOCUMENTOS_ESPERADOS = 26
POSICION_CONVOCATORIA = 15  # 1-indexado
DOCN_ESPERADO = "007960414"


class FalloDeContrato(AssertionError):
    pass


def verificar() -> None:
    contenido = descargar_rss(FECHA_CONOCIDA)

    cabecera = contenido[:100].decode("ascii", errors="replace")
    if "ISO-8859-1" not in cabecera.upper():
        raise FalloDeContrato(f"La cabecera XML ya no declara ISO-8859-1: {cabecera!r}")

    texto = contenido.decode("ISO-8859-1")
    raiz = ET.fromstring(texto)
    items = list(raiz.iter("item"))

    if len(items) != DOCUMENTOS_ESPERADOS:
        raise FalloDeContrato(
            f"Se esperaban {DOCUMENTOS_ESPERADOS} documentos el {FECHA_CONOCIDA}, "
            f"se han recibido {len(items)}"
        )

    for i, item in enumerate(items, start=1):
        for campo in ("title", "link", "pubDate"):
            if item.find(campo) is None:
                raise FalloDeContrato(f"Item {i} no tiene el campo '{campo}'")

    item_convocatoria = items[POSICION_CONVOCATORIA - 1]
    link = item_convocatoria.findtext("link") or ""
    if DOCN_ESPERADO not in link:
        raise FalloDeContrato(
            f"El documento en la posición {POSICION_CONVOCATORIA} ya no es "
            f"{DOCN_ESPERADO}: {link!r}"
        )

    url = construir_url(FECHA_CONOCIDA)
    if "RSSLST" not in url or "PUBL-C=" not in url:
        raise FalloDeContrato(f"La URL construida ya no tiene la forma esperada: {url}")


if __name__ == "__main__":
    try:
        verificar()
    except FalloDeContrato as exc:
        print(f"FALLO DE CONTRATO: {exc}")
        sys.exit(1)
    print(f"OK: el RSS del {FECHA_CONOCIDA} conserva la forma documentada.")
