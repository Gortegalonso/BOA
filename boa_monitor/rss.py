"""Colector A: descarga y parseo del RSS diario del BOA.

Fuente: https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI?CMD=RSSLST&...
Ver CLAUDE.md 7.1 y 7.1.1 para las trampas verificadas de este feed
(codificación ISO-8859-1, pubDate incorrecto, títulos con saltos de línea,
enlaces relativos con DOCN como clave de deduplicación).
"""

from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date

BASE_URL = "https://www.boa.aragon.es"
RSS_ENDPOINT = (
    f"{BASE_URL}/cgi-bin/EBOA/BRSCGI"
    "?CMD=RSSLST&DOCS=1-200&BASE=BOLE&SEC=BOARSS&SEPARADOR=&PUBL-C={fecha}"
)
USER_AGENT = "POT-Aragon-Monitor/0.1 (+contacto:koki87xla@gmail.com)"

_DOCN_RE = re.compile(r"DOCN=(\d+)")
_WHITESPACE_RE = re.compile(r"\s+")


class ErrorDescargaRSS(RuntimeError):
    pass


@dataclass(frozen=True)
class ItemBOA:
    docn: str
    titulo: str
    url: str
    fecha_boa: date


def construir_url(fecha: date) -> str:
    return RSS_ENDPOINT.format(fecha=fecha.strftime("%Y%m%d"))


def descargar_rss(fecha: date, intentos: int = 4, espera_inicial: float = 2.0) -> bytes:
    """Descarga el RSS crudo (bytes ISO-8859-1) para una fecha, con reintentos y backoff."""
    url = construir_url(fecha)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    ultimo_error: Exception | None = None
    espera = espera_inicial
    for intento in range(1, intentos + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            ultimo_error = exc
            if intento < intentos:
                time.sleep(espera)
                espera *= 2

    raise ErrorDescargaRSS(f"No se pudo descargar el RSS de {fecha} tras {intentos} intentos") from ultimo_error


def parsear_rss(contenido: bytes, fecha_boa: date) -> list[ItemBOA]:
    """Parsea el RSS crudo. `fecha_boa` se pasa explícitamente porque el
    campo pubDate del feed es incorrecto (día/mes intercambiados) y no debe
    usarse jamás como fuente de la fecha (CLAUDE.md 7.1.1, trampa 2)."""
    texto = contenido.decode("ISO-8859-1")
    raiz = ET.fromstring(texto)

    items: list[ItemBOA] = []
    for item in raiz.iter("item"):
        titulo_raw = (item.findtext("title") or "").strip()
        link_raw = (item.findtext("link") or "").strip()

        titulo = _WHITESPACE_RE.sub(" ", titulo_raw).strip()

        docn_match = _DOCN_RE.search(link_raw)
        if not docn_match:
            continue
        docn = docn_match.group(1)
        url = link_raw if link_raw.startswith("http") else f"{BASE_URL}{link_raw}"

        items.append(ItemBOA(docn=docn, titulo=titulo, url=url, fecha_boa=fecha_boa))

    return items


def obtener_items_del_dia(fecha: date) -> list[ItemBOA]:
    contenido = descargar_rss(fecha)
    return parsear_rss(contenido, fecha)
