"""Fase 3 (CLAUDE.md 10): backtest del filtro contra el conjunto de verdad.

Ejecutar: `python -m boa_monitor.backtest`

El conjunto de verdad (fixtures/regresion/positivos_esperados.json) se
construyó localizando a mano, vía el buscador avanzado del BOA
(BASE=BZHT, SEC=OPENDATABOAJSONELI), todas las órdenes de convocatoria y
sus correcciones de errores entre 2018 y 2026. Ver el hallazgo documentado
en CLAUDE.md: las listas de admitidos, calendarios, sedes y tribunales no
aparecen en el BOA en ese periodo — solo la orden y sus correcciones.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from boa_monitor.filtro import evaluar_titulo
from boa_monitor.rss import ItemBOA, parsear_rss

DIR_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "regresion"
FICHERO_POSITIVOS = DIR_FIXTURES / "positivos_esperados.json"


@dataclass
class ResultadoBacktest:
    total_documentos: int
    total_marcados: int
    total_esperados: int
    faltantes: dict[str, set[str]]  # fecha -> docns esperados que no se marcaron
    sorpresas: list[tuple[str, ItemBOA, tuple[str, ...]]]  # fecha, item, reglas

    @property
    def recall(self) -> float:
        if self.total_esperados == 0:
            return 1.0
        capturados = self.total_esperados - sum(len(v) for v in self.faltantes.values())
        return capturados / self.total_esperados

    @property
    def precision(self) -> float:
        if self.total_marcados == 0:
            return 0.0
        return (self.total_marcados - len(self.sorpresas)) / self.total_marcados


def ejecutar() -> ResultadoBacktest:
    positivos = json.loads(FICHERO_POSITIVOS.read_text(encoding="utf-8"))

    total_documentos = 0
    total_marcados = 0
    total_esperados = 0
    faltantes: dict[str, set[str]] = {}
    sorpresas: list[tuple[str, ItemBOA, tuple[str, ...]]] = []

    for fecha_str in sorted(positivos):
        fecha = date.fromisoformat(fecha_str)
        contenido = (DIR_FIXTURES / f"{fecha_str}.rss").read_bytes()
        items = parsear_rss(contenido, fecha)
        esperados = set(positivos[fecha_str]["docn_esperados"])

        marcados = [(item, evaluar_titulo(item.titulo)) for item in items]
        marcados = [(item, r) for item, r in marcados if r.marcado]

        total_documentos += len(items)
        total_marcados += len(marcados)
        total_esperados += len(esperados)

        docns_marcados = {item.docn for item, _ in marcados}
        faltan = esperados - docns_marcados
        if faltan:
            faltantes[fecha_str] = faltan

        for item, r in marcados:
            if item.docn not in esperados:
                sorpresas.append((fecha_str, item, r.reglas_disparadas))

    return ResultadoBacktest(
        total_documentos=total_documentos,
        total_marcados=total_marcados,
        total_esperados=total_esperados,
        faltantes=faltantes,
        sorpresas=sorpresas,
    )


if __name__ == "__main__":
    resultado = ejecutar()
    print(f"Documentos analizados: {resultado.total_documentos}")
    print(f"Marcados por el filtro: {resultado.total_marcados}")
    print(f"Positivos reales (conjunto de verdad): {resultado.total_esperados}")
    print(f"Recall: {resultado.recall:.1%}")
    print(f"Precisión: {resultado.precision:.1%}")
    if resultado.faltantes:
        print("\nFALSOS NEGATIVOS (esto bloquea el paso a fase 4):")
        for fecha_str, docns in resultado.faltantes.items():
            print(f"  {fecha_str}: {docns}")
    if resultado.sorpresas:
        print(f"\nFalsos positivos ({len(resultado.sorpresas)}):")
        for fecha_str, item, reglas in resultado.sorpresas:
            print(f"  {fecha_str} | {item.docn} | {reglas} | {item.titulo[:110]}")
