"""Orquestación del Colector A: descarga, cachea, filtra y registra.

Ejecutar directamente: `python -m boa_monitor.main [YYYY-MM-DD]`
Sin argumento usa la fecha de hoy.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

from boa_monitor.cache import (
    DIR_DATOS,
    cargar_vistos,
    guardar_raw,
    marcar_vistos,
)
from boa_monitor.filtro import ResultadoFiltro, evaluar_titulo
from boa_monitor.rss import ErrorDescargaRSS, ItemBOA, descargar_rss, parsear_rss

FICHERO_CONVOCATORIAS = DIR_DATOS / "convocatorias.json"
FICHERO_ESTADO = DIR_DATOS / "estado.json"


def _cargar_convocatorias() -> dict[str, dict]:
    if not FICHERO_CONVOCATORIAS.exists():
        return {}
    registros = json.loads(FICHERO_CONVOCATORIAS.read_text(encoding="utf-8"))
    return {r["docn"]: r for r in registros}


def _guardar_convocatorias(registros: dict[str, dict]) -> None:
    DIR_DATOS.mkdir(parents=True, exist_ok=True)
    lista = sorted(registros.values(), key=lambda r: (r["fecha_boa"], r["docn"]))
    FICHERO_CONVOCATORIAS.write_text(
        json.dumps(lista, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _registrar_marcados(marcados: list[tuple[ItemBOA, ResultadoFiltro]]) -> None:
    registros = _cargar_convocatorias()
    ahora = datetime.now(timezone.utc).isoformat()
    for item, resultado in marcados:
        registros[item.docn] = {
            "docn": item.docn,
            "titulo": item.titulo,
            "url": item.url,
            "fecha_boa": item.fecha_boa.isoformat(),
            "reglas_disparadas": list(resultado.reglas_disparadas),
            "cubo": resultado.cubo.value,
            "primera_deteccion_utc": ahora,
            "revisado": False,
        }
    _guardar_convocatorias(registros)


def _escribir_estado(
    fecha: date,
    documentos_totales: int,
    documentos_nuevos: int,
    documentos_marcados: int,
    error: str | None,
) -> None:
    DIR_DATOS.mkdir(parents=True, exist_ok=True)
    estado = {
        "ultima_ejecucion_utc": datetime.now(timezone.utc).isoformat(),
        "fecha_boa_consultada": fecha.isoformat(),
        "documentos_totales": documentos_totales,
        "documentos_nuevos": documentos_nuevos,
        "documentos_marcados": documentos_marcados,
        "error": error,
    }
    FICHERO_ESTADO.write_text(
        json.dumps(estado, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def colecta_diaria(fecha: date | None = None) -> dict:
    fecha = fecha or date.today()

    try:
        contenido = descargar_rss(fecha)
    except ErrorDescargaRSS as exc:
        _escribir_estado(fecha, documentos_totales=0, documentos_nuevos=0, documentos_marcados=0, error=str(exc))
        raise

    guardar_raw(fecha, contenido)
    items = parsear_rss(contenido, fecha)

    vistos = cargar_vistos()
    nuevos = [i for i in items if i.docn not in vistos]

    marcados = []
    for item in nuevos:
        resultado = evaluar_titulo(item.titulo)
        if resultado.marcado:
            marcados.append((item, resultado))

    if marcados:
        _registrar_marcados(marcados)

    marcar_vistos({i.docn for i in items})

    _escribir_estado(
        fecha,
        documentos_totales=len(items),
        documentos_nuevos=len(nuevos),
        documentos_marcados=len(marcados),
        error=None,
    )

    return {
        "fecha": fecha,
        "documentos_totales": len(items),
        "documentos_nuevos": len(nuevos),
        "marcados": marcados,
    }


if __name__ == "__main__":
    fecha_arg = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    resultado = colecta_diaria(fecha_arg)
    print(
        f"BOA {resultado['fecha']}: {resultado['documentos_totales']} documentos, "
        f"{resultado['documentos_nuevos']} nuevos, {len(resultado['marcados'])} marcados"
    )
    for item, filtro in resultado["marcados"]:
        print(f"  [{filtro.cubo.value}] {','.join(filtro.reglas_disparadas)} — {item.titulo[:100]}")
