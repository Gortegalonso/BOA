from pathlib import Path

import pytest

from boa_monitor import extraccion

FIXTURE_PDF = Path(__file__).resolve().parent.parent / "fixtures" / "educa" / "anexo_iii_calendario_pot_2026.pdf"

DATOS_VALIDOS = {
    "anio": 2026,
    "codigo_orden": "ECU/1145/2026",
    "fecha_orden": "2026-07-21",
    "fecha_publicacion_boa": "2026-08-06",
    "numero_boa": 151,
    "plazo_inscripcion_inicio": "2026-09-10",
    "plazo_inscripcion_fin": "2026-09-17",
    "modulos_convocados": [{"codigo": "0026", "denominacion": "Procesos de preelaboración"}],
    "modulos_excluidos": [],
    "sedes": [],
    "url_solicitud": None,
    "campos_no_encontrados": [],
}


def test_pdf_a_imagenes_produce_una_imagen_png_por_pagina():
    imagenes = extraccion.pdf_a_imagenes(FIXTURE_PDF)
    assert len(imagenes) == 1
    assert imagenes[0].startswith(b"\x89PNG")


def test_valida_datos_correctos_como_fiables():
    resultado = extraccion.validar_extraccion(DATOS_VALIDOS)
    assert resultado.fiable
    assert resultado.errores == ()


def test_detecta_orden_de_fechas_invertido():
    datos = dict(DATOS_VALIDOS, plazo_inscripcion_inicio="2026-09-20", plazo_inscripcion_fin="2026-09-17")
    resultado = extraccion.validar_extraccion(datos)
    assert not resultado.fiable
    assert any("orden de fechas" in e for e in resultado.errores)


def test_detecta_plazo_demasiado_largo():
    datos = dict(DATOS_VALIDOS, plazo_inscripcion_fin="2026-11-01")
    resultado = extraccion.validar_extraccion(datos)
    assert not resultado.fiable
    assert any("fuera de 5-40" in e for e in resultado.errores)


def test_detecta_plazo_que_empieza_demasiado_tarde():
    datos = dict(
        DATOS_VALIDOS,
        plazo_inscripcion_inicio="2026-11-01",
        plazo_inscripcion_fin="2026-11-10",
    )
    resultado = extraccion.validar_extraccion(datos)
    assert not resultado.fiable
    assert any("60 días" in e for e in resultado.errores)


def test_detecta_modulo_sin_codigo():
    datos = dict(DATOS_VALIDOS, modulos_convocados=[{"codigo": None, "denominacion": "Sin código"}])
    resultado = extraccion.validar_extraccion(datos)
    assert not resultado.fiable
    assert any("sin código o sin denominación" in e for e in resultado.errores)


def test_detecta_codigo_orden_con_formato_invalido():
    datos = dict(DATOS_VALIDOS, codigo_orden="orden-rara-2026")
    resultado = extraccion.validar_extraccion(datos)
    assert not resultado.fiable
    assert any("codigo_orden no casa" in e for e in resultado.errores)


def test_no_valida_plazos_si_faltan_fechas():
    # Regla 7 (CLAUDE.md): un campo ausente es null, no se inventa ni se
    # penaliza como si fuera un dato erróneo — campos_no_encontrados ya lo
    # registra por su cuenta.
    datos = dict(DATOS_VALIDOS, plazo_inscripcion_inicio=None, plazo_inscripcion_fin=None)
    resultado = extraccion.validar_extraccion(datos)
    assert resultado.fiable


def test_extraer_convocatoria_usa_el_segundo_proveedor_si_el_primero_falla(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-falsa")
    monkeypatch.setenv("MISTRAL_API_KEY", "clave-falsa")

    llamadas = []

    def _llamar_falso(proveedor, imagenes, prompt):
        llamadas.append(proveedor.nombre)
        if proveedor.nombre == "gemini":
            raise extraccion.ErrorExtraccion("gemini: fallo simulado")
        return dict(DATOS_VALIDOS)

    monkeypatch.setattr(extraccion, "_llamar_proveedor", _llamar_falso)

    datos = extraccion.extraer_convocatoria(FIXTURE_PDF)

    assert llamadas == ["gemini", "mistral"]
    assert datos["_proveedor_usado"] == "mistral"


def test_extraer_convocatoria_lanza_error_si_fallan_todos_los_proveedores(monkeypatch):
    def _llamar_falso(proveedor, imagenes, prompt):
        raise extraccion.ErrorExtraccion(f"{proveedor.nombre}: fallo simulado")

    monkeypatch.setattr(extraccion, "_llamar_proveedor", _llamar_falso)

    with pytest.raises(extraccion.ErrorExtraccion):
        extraccion.extraer_convocatoria(FIXTURE_PDF)


def test_llamar_proveedor_falla_rapido_sin_clave_de_api(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    proveedor = extraccion.PROVEEDORES[0]

    with pytest.raises(extraccion.ErrorExtraccion, match="GEMINI_API_KEY"):
        extraccion._llamar_proveedor(proveedor, [b"fake"], "prompt")
