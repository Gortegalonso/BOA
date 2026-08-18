"""Fase 6: cruce alumno-módulo (CLAUDE.md 7.6).

**Corregido el 18/08/2026 con datos reales**: la convocatoria NO cierra
módulo a módulo, cierra a nivel de título/ciclo. El Anexo II
("Títulos convocados y centros de realización de las pruebas") solo trae
código de título (p.ej. `HOT201`) y centro examinador; el propio Anexo I
(formulario de inscripción) trae la tabla de módulos profesionales EN
BLANCO para que cada alumno declare libremente cuáles necesita de su
título. Es decir: si el título está convocado, todos los módulos
pendientes de ese título son examinables en el centro asignado — no hay
una lista de módulos "convocados" por separado. Por eso el cruce compara
por `titulo_codigo_oficial` (+ `grado` como comprobación de coherencia), no
por `modulo_codigo`: ese campo se conserva porque es el que el alumno
declarará en el Anexo I, pero no participa en si está convocado.

El recorte a hostelería NO se aplica en la detección (regla 2 de 7.6/5) —
aquí sí, y de forma implícita: el Excel de alumnos lo trae el usuario ya
acotado a sus propios alumnos de hostelería, así que basta con comprobar
si el título de cada alumno aparece entre los `modulos_convocados` de la
extracción de la Fase 5 (pese al nombre del campo, heredado del esquema de
7.4, son entradas a nivel de título — ver más arriba).

El alumno nunca sale de la máquina local: `cargar_alumnos_excel` lee de una
ruta que el propio usuario indica, fuera del repositorio (sección 8).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import openpyxl  # excepción a "solo stdlib" (ver extraccion.py y CLAUDE.md
# sección 6): no hay forma de leer el formato binario .xlsx sin librería.

COLUMNAS = (
    "alumno_id",
    "nombre",
    "ciclo",
    "grado",
    "titulo_codigo_oficial",
    "modulo_codigo",
    "modulo_denominacion",
    "estado",
)


@dataclass(frozen=True)
class RegistroAlumno:
    alumno_id: str
    nombre: str
    ciclo: str  # código/nombre interno del centro — no se usa para cruzar,
    # solo para que el usuario identifique al alumno de un vistazo.
    grado: str
    titulo_codigo_oficial: str  # código oficial de Aragón (p.ej. "HOT201",
    # ver Anexo II) — esta es la clave real del cruce.
    modulo_codigo: str
    modulo_denominacion: str
    estado: str


@dataclass(frozen=True)
class ResultadoCruce:
    alumno_id: str
    nombre: str
    ciclo: str
    grado: str
    titulo_codigo_oficial: str
    modulo_codigo: str
    modulo_denominacion: str
    convocado_este_anio: bool
    centro_examinador: str | None
    fecha_limite_inscripcion: str | None
    advertencia: str | None  # p.ej. el grado declarado no casa con el de
    # la convocatoria para ese código — no bloquea el resultado (regla 1:
    # maximizar recall), pero pide revisión humana (7.7 de facto).


def cargar_alumnos_excel(ruta: Path) -> list[RegistroAlumno]:
    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    hoja = libro.active

    filas = hoja.iter_rows(values_only=True)
    cabecera = [str(c).strip() if c else "" for c in next(filas)]
    indice = {nombre: cabecera.index(nombre) for nombre in COLUMNAS if nombre in cabecera}
    faltan = [c for c in COLUMNAS if c not in indice]
    if faltan:
        raise ValueError(f"Faltan columnas obligatorias en {ruta.name}: {faltan}")

    registros = []
    for fila in filas:
        if all(v is None for v in fila):
            continue
        valores = {nombre: fila[i] for nombre, i in indice.items()}
        registros.append(
            RegistroAlumno(
                alumno_id=str(valores["alumno_id"]).strip(),
                nombre=str(valores["nombre"] or "").strip(),
                ciclo=str(valores["ciclo"] or "").strip(),
                grado=str(valores["grado"]).strip(),
                titulo_codigo_oficial=str(valores["titulo_codigo_oficial"]).strip(),
                modulo_codigo=str(valores["modulo_codigo"]).strip(),
                modulo_denominacion=str(valores["modulo_denominacion"] or "").strip(),
                estado=str(valores["estado"]).strip(),
            )
        )
    return registros


def cruzar(alumnos: list[RegistroAlumno], convocatoria: dict) -> list[ResultadoCruce]:
    convocados_por_codigo = {
        str(m["codigo"]).strip(): m for m in convocatoria.get("modulos_convocados") or [] if m.get("codigo")
    }
    fecha_limite = convocatoria.get("plazo_inscripcion_fin")

    resultados = []
    for alumno in alumnos:
        if alumno.estado != "pendiente":
            continue

        convocado = convocados_por_codigo.get(alumno.titulo_codigo_oficial)

        advertencia = None
        if convocado is not None:
            grado_convocatoria = str(convocado.get("grado") or "").strip().lower()
            grado_alumno = alumno.grado.strip().lower()
            if grado_convocatoria and grado_alumno and grado_convocatoria != grado_alumno:
                advertencia = (
                    f"el grado del alumno ({alumno.grado!r}) no casa con el de la convocatoria "
                    f"para {alumno.titulo_codigo_oficial} ({convocado.get('grado')!r}) — revisar a mano"
                )

        resultados.append(
            ResultadoCruce(
                alumno_id=alumno.alumno_id,
                nombre=alumno.nombre,
                ciclo=alumno.ciclo,
                grado=alumno.grado,
                titulo_codigo_oficial=alumno.titulo_codigo_oficial,
                modulo_codigo=alumno.modulo_codigo,
                modulo_denominacion=alumno.modulo_denominacion,
                convocado_este_anio=convocado is not None,
                centro_examinador=(convocado or {}).get("centro_examinador"),
                fecha_limite_inscripcion=fecha_limite if convocado is not None else None,
                advertencia=advertencia,
            )
        )
    return resultados


if __name__ == "__main__":
    import json
    import sys

    ruta_alumnos = Path(sys.argv[1])
    ruta_convocatoria = Path(sys.argv[2])

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    alumnos = cargar_alumnos_excel(ruta_alumnos)
    convocatoria = json.loads(ruta_convocatoria.read_text(encoding="utf-8"))
    resultados = cruzar(alumnos, convocatoria)

    pendientes_convocados = [r for r in resultados if r.convocado_este_anio]
    pendientes_no_convocados = [r for r in resultados if not r.convocado_este_anio]

    print(f"{len(resultados)} módulos pendientes en total")
    print(f"  {len(pendientes_convocados)} convocados este año:")
    for r in pendientes_convocados:
        aviso = f" — ⚠ {r.advertencia}" if r.advertencia else ""
        print(f"    {r.alumno_id} — {r.modulo_codigo} {r.modulo_denominacion} — centro: {r.centro_examinador}{aviso}")
    print(f"  {len(pendientes_no_convocados)} NO convocados este año:")
    for r in pendientes_no_convocados:
        print(f"    {r.alumno_id} — {r.titulo_codigo_oficial} — {r.modulo_codigo} {r.modulo_denominacion}")
