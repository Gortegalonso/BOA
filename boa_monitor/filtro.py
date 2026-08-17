"""Filtro determinista sobre los títulos del RSS (CLAUDE.md 7.3).

Maximiza recall, ignora precisión. Ninguna regla se retira jamás para
mejorar precisión: solo se amplían si el backtest revela un falso negativo.

El RSS no trae un campo de órgano estructurado (7.1.1), así que la regla R3
("órgano contiene educación") se evalúa contra el propio título completo:
es la señal más débil y por eso solo produce el cubo "ambiguo", nunca
"seguro". Ver la nota sobre el prefijo de la orden como señal auxiliar.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import Enum


def normalizar(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return sin_acentos.lower()


def _r1(t: str) -> bool:
    return "obtencion directa" in t and "titulo" in t


def _r2(t: str) -> bool:
    return "pruebas" in t and "formacion profesional" in t and ("tecnico" in t)


def _r3(t: str) -> bool:
    return "educ" in t and "prueb" in t


def _r4(t: str) -> bool:
    return "modulos profesionales" in t and ("convocan" in t or "convocatoria" in t)


REGLAS_FUERTES = {"R1": _r1, "R2": _r2, "R4": _r4}
REGLAS_DEBILES = {"R3": _r3}


class Cubo(str, Enum):
    SEGURO = "seguro"
    AMBIGUO = "ambiguo"
    DESCARTADO = "descartado"


@dataclass(frozen=True)
class ResultadoFiltro:
    reglas_disparadas: tuple[str, ...]
    cubo: Cubo

    @property
    def marcado(self) -> bool:
        return self.cubo is not Cubo.DESCARTADO


def evaluar_titulo(titulo: str) -> ResultadoFiltro:
    t = normalizar(titulo)

    fuertes = tuple(nombre for nombre, regla in REGLAS_FUERTES.items() if regla(t))
    debiles = tuple(nombre for nombre, regla in REGLAS_DEBILES.items() if regla(t))

    if fuertes:
        return ResultadoFiltro(reglas_disparadas=fuertes + debiles, cubo=Cubo.SEGURO)
    if debiles:
        return ResultadoFiltro(reglas_disparadas=debiles, cubo=Cubo.AMBIGUO)
    return ResultadoFiltro(reglas_disparadas=(), cubo=Cubo.DESCARTADO)
