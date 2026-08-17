import json
from datetime import date

from boa_monitor import alerta_estacional


def test_antes_del_10_de_septiembre_no_hay_nada_que_comprobar(monkeypatch, tmp_path):
    fichero = tmp_path / "convocatorias.json"
    monkeypatch.setattr(alerta_estacional, "FICHERO_CONVOCATORIAS", fichero)
    assert alerta_estacional.verificar(date(2026, 8, 17)) is True


def test_10_septiembre_sin_fichero_dispara_alerta(monkeypatch, tmp_path):
    fichero = tmp_path / "convocatorias.json"
    monkeypatch.setattr(alerta_estacional, "FICHERO_CONVOCATORIAS", fichero)
    assert alerta_estacional.verificar(date(2026, 9, 10)) is False


def test_10_septiembre_con_convocatoria_detectada_no_dispara_alerta(monkeypatch, tmp_path):
    fichero = tmp_path / "convocatorias.json"
    fichero.write_text(
        json.dumps(
            [
                {
                    "docn": "007960414",
                    "fecha_boa": "2026-08-06",
                    "cubo": "seguro",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(alerta_estacional, "FICHERO_CONVOCATORIAS", fichero)
    assert alerta_estacional.verificar(date(2026, 9, 10)) is True


def test_10_septiembre_con_solo_ambiguos_dispara_alerta(monkeypatch, tmp_path):
    fichero = tmp_path / "convocatorias.json"
    fichero.write_text(
        json.dumps(
            [
                {
                    "docn": "007960999",
                    "fecha_boa": "2026-07-15",
                    "cubo": "ambiguo",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(alerta_estacional, "FICHERO_CONVOCATORIAS", fichero)
    assert alerta_estacional.verificar(date(2026, 9, 10)) is False
