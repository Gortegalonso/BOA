import json
from datetime import date
from pathlib import Path

from boa_monitor import cache, main

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "regresion" / "2026-08-06.rss"


def _redirigir_datos_a_tmp(monkeypatch, tmp_path):
    dir_datos = tmp_path / "data"
    dir_cache = dir_datos / "cache_rss"
    fichero_vistos = dir_datos / "vistos.json"
    fichero_convocatorias = dir_datos / "convocatorias.json"
    fichero_estado = dir_datos / "estado.json"

    monkeypatch.setattr(cache, "DIR_DATOS", dir_datos)
    monkeypatch.setattr(cache, "DIR_CACHE_RSS", dir_cache)
    monkeypatch.setattr(cache, "FICHERO_VISTOS", fichero_vistos)
    monkeypatch.setattr(main, "DIR_DATOS", dir_datos)
    monkeypatch.setattr(main, "FICHERO_CONVOCATORIAS", fichero_convocatorias)
    monkeypatch.setattr(main, "FICHERO_ESTADO", fichero_estado)
    return fichero_convocatorias, fichero_estado


def test_colecta_diaria_detecta_y_registra_la_convocatoria(monkeypatch, tmp_path):
    fichero_convocatorias, fichero_estado = _redirigir_datos_a_tmp(monkeypatch, tmp_path)
    monkeypatch.setattr(main, "descargar_rss", lambda fecha: FIXTURE.read_bytes())

    resultado = main.colecta_diaria(date(2026, 8, 6))

    assert resultado["documentos_totales"] == 26
    assert len(resultado["marcados"]) == 1

    convocatorias = json.loads(fichero_convocatorias.read_text(encoding="utf-8"))
    assert len(convocatorias) == 1
    assert convocatorias[0]["docn"] == "007960414"
    assert convocatorias[0]["cubo"] == "seguro"

    estado = json.loads(fichero_estado.read_text(encoding="utf-8"))
    assert estado["documentos_marcados"] == 1
    assert estado["error"] is None


def test_segunda_ejecucion_mismo_dia_no_duplica_ni_re_marca(monkeypatch, tmp_path):
    fichero_convocatorias, fichero_estado = _redirigir_datos_a_tmp(monkeypatch, tmp_path)
    monkeypatch.setattr(main, "descargar_rss", lambda fecha: FIXTURE.read_bytes())

    main.colecta_diaria(date(2026, 8, 6))
    resultado_2 = main.colecta_diaria(date(2026, 8, 6))

    assert resultado_2["documentos_nuevos"] == 0
    assert len(resultado_2["marcados"]) == 0

    convocatorias = json.loads(fichero_convocatorias.read_text(encoding="utf-8"))
    assert len(convocatorias) == 1
