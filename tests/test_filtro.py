from boa_monitor.filtro import Cubo, evaluar_titulo, normalizar

TITULO_REAL_2026 = (
    "BOA 6/08/26 - ORDEN ECU/1145/2026, de 21 de julio, por la que se convocan las "
    "pruebas para la obtención directa de los títulos de Técnico y Técnico Superior "
    "de Formación Profesional en la Comunidad Autónoma de Aragón, correspondientes "
    "al año 2026."
)

TITULO_REAL_2025 = (
    "BOA 4/08/25 - ORDEN ECD/941/2025, de 24 de julio, por la que se convocan las "
    "pruebas para la obtención directa de los títulos de Técnico y Técnico Superior "
    "de Formación Profesional en la Comunidad Autónoma de Aragón."
)


def test_normalizar_quita_acentos_y_pasa_a_minusculas():
    assert normalizar("Obtención Directa de Títulos") == "obtencion directa de titulos"


def test_normalizar_no_toca_los_espacios():
    # El colapso de saltos de línea internos del título (trampa 3 de 7.1.1) es
    # responsabilidad de rss.parsear_rss, no de esta función.
    assert normalizar("Título de\ntécnico") == "titulo de\ntecnico"


def test_convocatoria_2026_dispara_r1_y_r2():
    resultado = evaluar_titulo(TITULO_REAL_2026)
    assert resultado.cubo is Cubo.SEGURO
    assert "R1" in resultado.reglas_disparadas
    assert "R2" in resultado.reglas_disparadas


def test_convocatoria_2025_prefijo_ecd_tambien_dispara():
    resultado = evaluar_titulo(TITULO_REAL_2025)
    assert resultado.cubo is Cubo.SEGURO


def test_robustez_quitando_la_palabra_directa():
    titulo = TITULO_REAL_2026.replace("obtención directa", "obtención")
    resultado = evaluar_titulo(titulo)
    assert resultado.cubo is Cubo.SEGURO, "R2 debe seguir disparando aunque falte 'directa'"
    assert "R2" in resultado.reglas_disparadas


def test_robustez_cambiando_pruebas_por_prueba_singular():
    titulo = TITULO_REAL_2026.replace("pruebas para la obtención directa", "prueba para la obtención directa")
    resultado = evaluar_titulo(titulo)
    assert resultado.cubo is Cubo.SEGURO, "R1 no depende de 'pruebas' y debe seguir disparando"


def test_robustez_cambiando_prefijo_de_orden():
    titulo = TITULO_REAL_2026.replace("ECU/1145/2026", "XYZ/9999/2026")
    resultado = evaluar_titulo(titulo)
    assert resultado.cubo is Cubo.SEGURO, "El filtro no debe depender del prefijo de la orden"


def test_documento_no_relacionado_no_dispara_nada():
    titulo = (
        "BOA 6/08/26 - RESOLUCIÓN de 27 de julio de 2026, del Director General de "
        "Justicia, por la que se corrigen errores en la relación de plazas del "
        "Cuerpo de Gestión Procesal y Administrativa."
    )
    resultado = evaluar_titulo(titulo)
    assert resultado.cubo is Cubo.DESCARTADO


def test_orden_ecu_sin_mencion_de_pruebas_no_dispara_r3():
    titulo = (
        "BOA 6/08/26 - ORDEN ECU/1148/2026, de 22 de julio, por la que se convoca "
        "el proceso de admisión de alumnado oficial en las Escuelas Oficiales de "
        "Idiomas de la Comunidad Autónoma de Aragón."
    )
    resultado = evaluar_titulo(titulo)
    assert resultado.cubo is Cubo.DESCARTADO
