"""Colector B: páginas de educa.aragon.es (CLAUDE.md 7.2).

A diferencia del BOA, aquí no hay un feed estructurado: se extrae el
conjunto de enlaces a PDF de cada página vigilada y se compara con el
conjunto guardado en la ejecución anterior. La clave de comparación es la
URL completa del PDF (no el texto del enlace), porque el gestor documental
del sitio (Liferay) incrusta un identificador de versión en la propia URL:
si el Departamento sustituye un PDF por una versión corregida manteniendo
el mismo texto de enlace ("Convocatoria actual."), la URL cambia y el
diff lo detecta igual. No se hashea la página entera (7.2): elementos
volátiles (banners, fechas de "última actualización") generarían falsas
alarmas a diario sin decir qué documento es nuevo.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://educa.aragon.es"
USER_AGENT = "POT-Aragon-Monitor/0.1 (+contacto:koki87xla@gmail.com)"

PAGINAS_VIGILADAS = {
    "pots_calendario": "/-/formacion-profesional/calendario/pots",
}

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
DIR_DATOS = RAIZ_PROYECTO / "data"
FICHERO_ESTADO_EDUCA = DIR_DATOS / "estado_educa.json"
FICHERO_DOCUMENTOS_EDUCA = DIR_DATOS / "documentos_educa.json"

_ENLACE_PDF_RE = re.compile(
    r'<a[^>]*href="([^"]+\.pdf[^"]*)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class ErrorDescargaEduca(RuntimeError):
    pass


@dataclass(frozen=True)
class EnlacePDF:
    url: str
    texto: str


def descargar_pagina(ruta: str, intentos: int = 4, espera_inicial: float = 2.0) -> str:
    url = ruta if ruta.startswith("http") else f"{BASE_URL}{ruta}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    ultimo_error: Exception | None = None
    espera = espera_inicial
    for intento in range(1, intentos + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            ultimo_error = exc
            if intento < intentos:
                time.sleep(espera)
                espera *= 2

    raise ErrorDescargaEduca(f"No se pudo descargar {url} tras {intentos} intentos") from ultimo_error


def extraer_enlaces_pdf(html: str) -> list[EnlacePDF]:
    enlaces = []
    for match in _ENLACE_PDF_RE.finditer(html):
        url_relativa = match.group(1)
        texto_crudo = _TAG_RE.sub(" ", match.group(2))
        texto = _WHITESPACE_RE.sub(" ", texto_crudo).strip()
        url = url_relativa if url_relativa.startswith("http") else f"{BASE_URL}{url_relativa}"
        enlaces.append(EnlacePDF(url=url, texto=texto))
    return enlaces


def _cargar_estado() -> dict:
    if not FICHERO_ESTADO_EDUCA.exists():
        return {}
    return json.loads(FICHERO_ESTADO_EDUCA.read_text(encoding="utf-8"))


def _guardar_estado(estado: dict) -> None:
    DIR_DATOS.mkdir(parents=True, exist_ok=True)
    FICHERO_ESTADO_EDUCA.write_text(
        json.dumps(estado, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _registrar_documentos_nuevos(pagina_id: str, nuevos: list[EnlacePDF]) -> None:
    if not FICHERO_DOCUMENTOS_EDUCA.exists():
        registros = []
    else:
        registros = json.loads(FICHERO_DOCUMENTOS_EDUCA.read_text(encoding="utf-8"))

    ahora = datetime.now(timezone.utc).isoformat()
    urls_existentes = {r["url"] for r in registros}
    for enlace in nuevos:
        if enlace.url in urls_existentes:
            continue
        registros.append(
            {
                "url": enlace.url,
                "texto": enlace.texto,
                "pagina_origen": pagina_id,
                "primera_deteccion_utc": ahora,
                "revisado": False,
            }
        )

    DIR_DATOS.mkdir(parents=True, exist_ok=True)
    FICHERO_DOCUMENTOS_EDUCA.write_text(
        json.dumps(registros, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def colecta_educa(paginas: dict[str, str] | None = None) -> dict:
    paginas = paginas if paginas is not None else PAGINAS_VIGILADAS
    estado = _cargar_estado()
    ahora = datetime.now(timezone.utc).isoformat()

    resultado_por_pagina = {}
    for pagina_id, ruta in paginas.items():
        try:
            html = descargar_pagina(ruta)
            error = None
        except ErrorDescargaEduca as exc:
            resultado_por_pagina[pagina_id] = {"error": str(exc), "nuevos": []}
            continue

        enlaces = extraer_enlaces_pdf(html)
        enlaces_por_url = {e.url: e.texto for e in enlaces}

        anterior = estado.get(pagina_id, {}).get("enlaces", {})
        urls_nuevas = set(enlaces_por_url) - set(anterior)
        nuevos = [EnlacePDF(url=u, texto=enlaces_por_url[u]) for u in urls_nuevas]

        if nuevos:
            _registrar_documentos_nuevos(pagina_id, nuevos)

        estado[pagina_id] = {
            "enlaces": enlaces_por_url,
            "ultima_comprobacion_utc": ahora,
            "total_enlaces": len(enlaces_por_url),
        }
        resultado_por_pagina[pagina_id] = {"error": error, "nuevos": nuevos}

    _guardar_estado(estado)
    return resultado_por_pagina


if __name__ == "__main__":
    resultado = colecta_educa()
    for pagina_id, info in resultado.items():
        if info["error"]:
            print(f"{pagina_id}: ERROR — {info['error']}")
            continue
        print(f"{pagina_id}: {len(info['nuevos'])} documento(s) nuevo(s)")
        for enlace in info["nuevos"]:
            print(f"  {enlace.texto} -> {enlace.url}")
