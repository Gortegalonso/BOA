"""Fase 5: extracción con LLM de los PDF de la convocatoria (CLAUDE.md 7.4-7.5).

El LLM solo convierte PDF en JSON; nunca decide si el documento es relevante
(eso ya lo hizo el filtro determinista o el Colector B) y nunca es la última
palabra sobre si el resultado es fiable (regla 4 y 7.5: la validación
determinista decide eso, en `validar_extraccion`).

Entrada como imágenes, no texto extraído: las tablas del BOA se desordenan al
pasarlas a texto plano (7.4). Se prueban dos proveedores gratuitos con API
compatible con OpenAI, en orden, con fallback automático — 7.4 exige esto
precisamente porque los proveedores retiran modelos gratuitos sin aviso (le
pasó a los modelos de visión de Groq durante 2026, por eso no está en esta
lista pese a ser buen candidato en velocidad).
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pymupdf  # única dependencia de runtime fuera de la stdlib en todo
# boa_monitor (ver CLAUDE.md sección 6); no hay forma de renderizar PDF a
# imagen con la librería estándar de Python.

USER_AGENT = "POT-Aragon-Monitor/0.1 (+contacto:koki87xla@gmail.com)"


class ErrorExtraccion(RuntimeError):
    pass


@dataclass(frozen=True)
class Proveedor:
    nombre: str
    base_url: str
    modelo: str
    variable_clave: str


PROVEEDORES: tuple[Proveedor, ...] = (
    Proveedor(
        nombre="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        modelo="gemini-flash-latest",
        variable_clave="GEMINI_API_KEY",
    ),
    Proveedor(
        nombre="mistral",
        base_url="https://api.mistral.ai/v1/chat/completions",
        modelo="mistral-large-latest",
        variable_clave="MISTRAL_API_KEY",
    ),
)

PROMPT_EXTRACCION = """\
Eres un extractor de datos, no un intérprete. Vas a recibir las páginas de un
documento oficial (BOA de Aragón o anexo de educa.aragon.es) sobre la
convocatoria de pruebas de obtención de títulos de FP.

Devuelve ÚNICAMENTE un JSON con este esquema exacto, sin texto adicional:

{
  "anio": null,
  "codigo_orden": null,
  "fecha_orden": null,
  "fecha_publicacion_boa": null,
  "numero_boa": null,
  "plazo_inscripcion_inicio": null,
  "plazo_inscripcion_fin": null,
  "modulos_convocados": [
    {"codigo": null, "denominacion": null, "ciclo": null, "grado": null, "centro_examinador": null}
  ],
  "modulos_excluidos": [],
  "sedes": [],
  "url_solicitud": null,
  "campos_no_encontrados": []
}

Reglas estrictas:
- Fechas en formato ISO "AAAA-MM-DD".
- Si un dato no aparece en el documento, su valor es `null` (o lista vacía
  si es una lista). Nunca lo inventes ni lo infieras de otro campo.
- Añade a "campos_no_encontrados" el nombre de cada campo de nivel superior
  que no hayas podido rellenar.
- Si el documento no trae módulos, "modulos_convocados" es una lista vacía,
  no una lista con un elemento de campos nulos.
"""


def pdf_a_imagenes(ruta_pdf: Path, zoom: float = 2.0) -> list[bytes]:
    imagenes = []
    with pymupdf.open(ruta_pdf) as documento:
        for pagina in documento:
            pixmap = pagina.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
            imagenes.append(pixmap.tobytes("png"))
    return imagenes


def _construir_cuerpo_peticion(proveedor: Proveedor, imagenes: list[bytes], prompt: str) -> dict:
    contenido: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for imagen in imagenes:
        b64 = base64.b64encode(imagen).decode("ascii")
        contenido.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            }
        )
    return {
        "model": proveedor.modelo,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": contenido}],
    }


def _llamar_proveedor(
    proveedor: Proveedor,
    imagenes: list[bytes],
    prompt: str,
    intentos: int = 3,
    espera_inicial: float = 5.0,
    timeout: float = 240.0,
) -> dict:
    clave = os.environ.get(proveedor.variable_clave)
    if not clave:
        raise ErrorExtraccion(f"{proveedor.nombre}: falta la variable de entorno {proveedor.variable_clave}")

    cuerpo = json.dumps(_construir_cuerpo_peticion(proveedor, imagenes, prompt)).encode("utf-8")
    peticion = urllib.request.Request(
        proveedor.base_url,
        data=cuerpo,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Authorization": f"Bearer {clave}",
        },
        method="POST",
    )

    ultimo_error: Exception | None = None
    espera = espera_inicial
    for intento in range(1, intentos + 1):
        try:
            with urllib.request.urlopen(peticion, timeout=timeout) as resp:
                respuesta = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            # Errores 4xx (clave inválida, petición mal formada...) son
            # permanentes: reintentar no los arregla. Solo los 5xx —
            # sobrecarga temporal del proveedor, como el 503 de Gemini
            # observado el 18/08/2026 — merecen reintento con backoff.
            if exc.code < 500:
                raise ErrorExtraccion(f"{proveedor.nombre}: HTTP {exc.code} — {exc.reason}") from exc
            ultimo_error = exc
            if intento < intentos:
                time.sleep(espera)
                espera *= 2
        except (urllib.error.URLError, TimeoutError) as exc:
            ultimo_error = exc
            if intento < intentos:
                time.sleep(espera)
                espera *= 2
    else:
        raise ErrorExtraccion(f"{proveedor.nombre}: fallo de red tras {intentos} intentos — {ultimo_error}") from ultimo_error

    try:
        contenido = respuesta["choices"][0]["message"]["content"]
        return json.loads(contenido)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise ErrorExtraccion(f"{proveedor.nombre}: respuesta no es el JSON esperado — {exc}") from exc


def extraer_convocatoria(
    ruta_pdf: Path,
    proveedores: tuple[Proveedor, ...] = PROVEEDORES,
    prompt: str = PROMPT_EXTRACCION,
) -> dict:
    imagenes = pdf_a_imagenes(ruta_pdf)

    errores: list[str] = []
    for proveedor in proveedores:
        try:
            datos = _llamar_proveedor(proveedor, imagenes, prompt)
        except ErrorExtraccion as exc:
            errores.append(str(exc))
            continue
        datos["_proveedor_usado"] = proveedor.nombre
        return datos

    raise ErrorExtraccion(
        f"Todos los proveedores fallaron para {ruta_pdf.name}: " + "; ".join(errores)
    )


_CODIGO_ORDEN_RE = re.compile(r"^[A-Z]{2,4}/\d+/\d{4}$")


@dataclass(frozen=True)
class ResultadoValidacion:
    fiable: bool
    errores: tuple[str, ...]


def validar_extraccion(datos: dict) -> ResultadoValidacion:
    errores: list[str] = []

    codigo_orden = datos.get("codigo_orden")
    if codigo_orden is not None and not _CODIGO_ORDEN_RE.match(codigo_orden):
        errores.append(f"codigo_orden no casa con [A-Z]{{2,4}}/N/AAAA: {codigo_orden!r}")

    for i, modulo in enumerate(datos.get("modulos_convocados") or []):
        if not modulo.get("codigo") or not modulo.get("denominacion"):
            errores.append(f"modulos_convocados[{i}] sin código o sin denominación: {modulo!r}")

    inicio = datos.get("plazo_inscripcion_inicio")
    fin = datos.get("plazo_inscripcion_fin")
    publicacion = datos.get("fecha_publicacion_boa")
    if inicio and fin and publicacion:
        try:
            f_inicio = date.fromisoformat(inicio)
            f_fin = date.fromisoformat(fin)
            f_publicacion = date.fromisoformat(publicacion)
        except ValueError as exc:
            errores.append(f"fecha con formato inválido: {exc}")
        else:
            if not (f_fin > f_inicio > f_publicacion):
                errores.append(
                    f"orden de fechas inválido: publicacion={f_publicacion} inicio={f_inicio} fin={f_fin}"
                )
            else:
                duracion = (f_fin - f_inicio).days
                if not (5 <= duracion <= 40):
                    errores.append(f"plazo de inscripción de {duracion} días, fuera de 5-40")
                if (f_inicio - f_publicacion).days >= 60:
                    errores.append("el plazo empieza 60 días o más después de la publicación en el BOA")

    return ResultadoValidacion(fiable=not errores, errores=tuple(errores))


if __name__ == "__main__":
    import sys

    # En Windows, print() usa la codificación de la consola (típicamente
    # cp1252) en vez de UTF-8 al escribir, tanto en pantalla como redirigido
    # a fichero — corrompe los acentos del JSON de salida (detectado el
    # 18/08/2026 al guardar la extracción real del Anexo II).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ruta = Path(sys.argv[1])
    datos = extraer_convocatoria(ruta)
    print(json.dumps(datos, ensure_ascii=False, indent=2))

    resultado = validar_extraccion(datos)
    if resultado.fiable:
        print("\nValidación: OK")
    else:
        print("\nValidación: NO FIABLE — alertar igualmente (7.5), revisar a mano:")
        for error in resultado.errores:
            print(f"  - {error}")
