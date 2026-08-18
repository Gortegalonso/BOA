from pathlib import Path

import openpyxl
import pytest

from boa_monitor import cruce

FIXTURE_ALUMNOS = Path(__file__).resolve().parent.parent / "fixtures" / "cruce" / "alumnos_ejemplo.xlsx"

# Subconjunto real de la extracción de la Fase 5 sobre el Anexo II 2026
# (18/08/2026): la convocatoria cierra a nivel de título, no de módulo — ver
# la cabecera de boa_monitor/cruce.py.
CONVOCATORIA_EJEMPLO = {
    "plazo_inscripcion_fin": "2026-09-17",
    "modulos_convocados": [
        {"codigo": "HOT201", "denominacion": "Técnico/a en Cocina y Gastronomía", "grado": "Medio", "centro_examinador": "CPIFP San Lorenzo"},
        {"codigo": "HOT203", "denominacion": "Técnico/a en Servicios de Restauración", "grado": "Medio", "centro_examinador": "CPIFP San Lorenzo"},
        {"codigo": "HOT305", "denominacion": "Técnico/a Superior en Dirección de Cocina", "grado": "Superior", "centro_examinador": "CPIFP Escuela de Hostelería y Turismo de Teruel"},
    ],
}


def test_carga_los_ocho_registros_del_excel_de_ejemplo():
    alumnos = cruce.cargar_alumnos_excel(FIXTURE_ALUMNOS)
    assert len(alumnos) == 8
    assert alumnos[0].alumno_id == "A001"
    assert alumnos[0].titulo_codigo_oficial == "HOT201"
    assert alumnos[0].estado == "pendiente"


def test_cruzar_descarta_modulos_no_pendientes():
    alumnos = cruce.cargar_alumnos_excel(FIXTURE_ALUMNOS)
    resultados = cruce.cruzar(alumnos, CONVOCATORIA_EJEMPLO)
    # De los 8 registros, 2 no son "pendiente" (superado, convalidado): quedan 6.
    assert len(resultados) == 6
    assert all(r.alumno_id != "A002" for r in resultados)  # A002 solo tenía un módulo, superado


def test_cruzar_marca_convocado_por_titulo_no_por_modulo():
    # A001 tiene DOS módulos pendientes del mismo título (HOT201). El título
    # está convocado, así que los dos deben salir como convocados — no hay
    # una lista de módulos convocados por separado (ver cabecera del módulo).
    alumnos = cruce.cargar_alumnos_excel(FIXTURE_ALUMNOS)
    resultados = [r for r in cruce.cruzar(alumnos, CONVOCATORIA_EJEMPLO) if r.alumno_id == "A001"]
    assert len(resultados) == 2
    assert all(r.convocado_este_anio for r in resultados)
    assert all(r.centro_examinador == "CPIFP San Lorenzo" for r in resultados)
    assert all(r.fecha_limite_inscripcion == "2026-09-17" for r in resultados)


def test_cruzar_marca_titulo_no_convocado():
    alumnos = cruce.cargar_alumnos_excel(FIXTURE_ALUMNOS)
    resultados = {r.alumno_id: r for r in cruce.cruzar(alumnos, CONVOCATORIA_EJEMPLO)}

    no_convocado = resultados["A005"]  # HOT999, código inventado, no existe en la convocatoria
    assert not no_convocado.convocado_este_anio
    assert no_convocado.centro_examinador is None
    assert no_convocado.fecha_limite_inscripcion is None


def test_cruzar_avisa_si_el_grado_no_casa_con_la_convocatoria():
    # A006 declara HOT201 (que en la convocatoria real es de grado Medio)
    # pero con grado "superior" — un error de transcripción típico que
    # nunca debe pasar desapercibido (7.6: un módulo mal solicitado cuesta
    # un año).
    alumnos = cruce.cargar_alumnos_excel(FIXTURE_ALUMNOS)
    resultados = {r.alumno_id: r for r in cruce.cruzar(alumnos, CONVOCATORIA_EJEMPLO)}

    con_aviso = resultados["A006"]
    assert con_aviso.convocado_este_anio  # el código sí está convocado...
    assert con_aviso.advertencia is not None  # ...pero el grado no casa, y eso se avisa
    assert "grado" in con_aviso.advertencia

    sin_aviso = resultados["A001"]
    assert sin_aviso.advertencia is None


def test_cruzar_con_convocatoria_vacia_no_marca_nada_como_convocado():
    alumnos = cruce.cargar_alumnos_excel(FIXTURE_ALUMNOS)
    resultados = cruce.cruzar(alumnos, {"modulos_convocados": [], "plazo_inscripcion_fin": None})
    assert all(not r.convocado_este_anio for r in resultados)


def test_cargar_alumnos_excel_lanza_error_si_falta_una_columna_obligatoria(tmp_path):
    ruta = tmp_path / "alumnos_incompleto.xlsx"
    libro = openpyxl.Workbook()
    hoja = libro.active
    # Sin "titulo_codigo_oficial": justo la columna que ahora hace de clave del cruce.
    hoja.append(("alumno_id", "nombre", "ciclo", "grado", "modulo_codigo", "modulo_denominacion", "estado"))
    hoja.append(("A001", "Ana Pérez", "COCI", "medio", "0026", "Procesos de preelaboración", "pendiente"))
    libro.save(ruta)

    with pytest.raises(ValueError, match="titulo_codigo_oficial"):
        cruce.cargar_alumnos_excel(ruta)
