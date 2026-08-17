import json
from pathlib import Path

from boa_monitor import educa

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "educa" / "pots_calendario_2026-08-17.html"


def _html():
    return FIXTURE.read_text(encoding="utf-8")


def test_extrae_los_cuatro_pdf_de_la_pagina_real():
    enlaces = educa.extraer_enlaces_pdf(_html())
    assert len(enlaces) == 4
    urls = {e.url for e in enlaces}
    assert all(u.startswith("https://educa.aragon.es/documents/") for u in urls)


def test_el_texto_del_enlace_no_tiene_etiquetas_ni_saltos():
    enlaces = educa.extraer_enlaces_pdf(_html())
    textos = {e.texto for e in enlaces}
    assert "Calendario de la convocatoria" in textos
    assert not any("<" in t for t in textos)


def _redirigir_datos_a_tmp(monkeypatch, tmp_path):
    dir_datos = tmp_path / "data"
    fichero_estado = dir_datos / "estado_educa.json"
    fichero_documentos = dir_datos / "documentos_educa.json"
    monkeypatch.setattr(educa, "DIR_DATOS", dir_datos)
    monkeypatch.setattr(educa, "FICHERO_ESTADO_EDUCA", fichero_estado)
    monkeypatch.setattr(educa, "FICHERO_DOCUMENTOS_EDUCA", fichero_documentos)
    return fichero_estado, fichero_documentos


def test_primera_ejecucion_marca_todo_lo_existente_como_nuevo_y_fija_la_linea_base(monkeypatch, tmp_path):
    # La primera vez que se vigila una página no hay "día anterior" con el que
    # comparar, así que todo lo que hay ahora cuenta como "nuevo para el
    # sistema" (igual que el primer día de Colector A marca lo que encuentra
    # ese día). A partir de la segunda ejecución ya compara contra esta línea
    # base guardada.
    fichero_estado, fichero_documentos = _redirigir_datos_a_tmp(monkeypatch, tmp_path)
    monkeypatch.setattr(educa, "descargar_pagina", lambda ruta: _html())

    resultado = educa.colecta_educa({"pots_calendario": "/-/formacion-profesional/calendario/pots"})

    assert len(resultado["pots_calendario"]["nuevos"]) == 4
    estado = json.loads(fichero_estado.read_text(encoding="utf-8"))
    assert estado["pots_calendario"]["total_enlaces"] == 4


def test_segunda_ejecucion_sin_cambios_no_detecta_nada_nuevo(monkeypatch, tmp_path):
    _redirigir_datos_a_tmp(monkeypatch, tmp_path)
    monkeypatch.setattr(educa, "descargar_pagina", lambda ruta: _html())

    paginas = {"pots_calendario": "/-/formacion-profesional/calendario/pots"}
    educa.colecta_educa(paginas)
    resultado_2 = educa.colecta_educa(paginas)

    assert resultado_2["pots_calendario"]["nuevos"] == []


def test_documento_nuevo_se_detecta_por_url_no_por_texto(monkeypatch, tmp_path):
    # Simula el "día anterior": la misma página pero sin el Anexo III
    # (calendario) y con la "Convocatoria actual" apuntando a otra URL (como
    # si el Departamento hubiera sustituido el PDF por una corrección).
    fichero_estado, fichero_documentos = _redirigir_datos_a_tmp(monkeypatch, tmp_path)
    html_dia_anterior = (
        _html()
        .replace(
            "/documents/20126/6898806/BRSCGI.pdf/ce1c1cc6-4e9c-850f-9dcb-d8e71b1e99f3?t=1786341049604",
            "/documents/20126/6898806/BRSCGI.pdf/version-anterior?t=1",
        )
        .replace(
            '<a href="/documents/20126/6840006/Anexo+III+Orden+POT_2026+v3.pdf/71754966-925c-2a80-159c-864c2f658a5a?t=1784544338491" target="">Calendario de la convocatoria</a>',
            "",
        )
    )
    paginas = {"pots_calendario": "/-/formacion-profesional/calendario/pots"}

    monkeypatch.setattr(educa, "descargar_pagina", lambda ruta: html_dia_anterior)
    resultado_1 = educa.colecta_educa(paginas)
    assert len(resultado_1["pots_calendario"]["nuevos"]) == 3  # sin el calendario

    monkeypatch.setattr(educa, "descargar_pagina", lambda ruta: _html())
    resultado_2 = educa.colecta_educa(paginas)
    nuevos_2 = {e.url for e in resultado_2["pots_calendario"]["nuevos"]}

    assert len(nuevos_2) == 2  # el calendario (nuevo) + la convocatoria (URL sustituida)
    assert any("Anexo+III" in u for u in nuevos_2)
    assert any("ce1c1cc6" in u for u in nuevos_2)

    documentos = json.loads(fichero_documentos.read_text(encoding="utf-8"))
    assert len(documentos) == 3 + 2  # los 3 de la primera vez + los 2 nuevos
