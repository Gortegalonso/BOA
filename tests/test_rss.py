from datetime import date
from pathlib import Path

from boa_monitor.rss import construir_url, parsear_rss

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "regresion" / "2026-08-06.rss"


def _cargar_items():
    contenido = FIXTURE.read_bytes()
    return parsear_rss(contenido, date(2026, 8, 6))


def test_construir_url_usa_publc_con_formato_aaaammdd():
    url = construir_url(date(2026, 8, 6))
    assert "PUBL-C=20260806" in url
    assert url.startswith("https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI")


def test_parsea_los_26_documentos_del_boletin():
    items = _cargar_items()
    assert len(items) == 26


def test_docn_es_secuencial_sin_huecos():
    items = _cargar_items()
    docns = [int(i.docn) for i in items]
    assert docns == list(range(docns[0], docns[0] + 26))


def test_encuentra_la_orden_de_convocatoria_en_la_posicion_15():
    items = _cargar_items()
    item = items[14]
    assert item.docn == "007960414"
    assert "ECU/1145/2026" in item.titulo
    assert "obtención directa" in item.titulo


def test_titulos_no_tienen_saltos_de_linea_internos():
    items = _cargar_items()
    assert all("\n" not in i.titulo for i in items)


def test_url_es_absoluta_y_usa_verdoc():
    items = _cargar_items()
    for item in items:
        assert item.url.startswith("https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI?CMD=VERDOC")


def test_fecha_boa_no_se_toma_del_puddate_del_feed():
    # El pubDate del feed viene con día/mes intercambiados (trampa 2 de 7.1.1);
    # fecha_boa debe ser exactamente la fecha pasada como parámetro, no derivada del XML.
    items = _cargar_items()
    assert all(i.fecha_boa == date(2026, 8, 6) for i in items)
