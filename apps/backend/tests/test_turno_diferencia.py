"""`Turno.diferencia` (S3.8): la columna ya existía en el schema real (mirror
de prod del baseline) pero el ORM nunca la mapeaba — `_get_turno_diferencia`
siempre devolvía `None`. Con el modelo actualizado, `cerrar_turno` debe
persistirla de verdad, no solo calcularla y descartarla.
"""

CONTEO = {"denominaciones": [{"denominacion": 100, "cantidad": 5}]}  # $500


def test_cerrar_turno_persiste_diferencia(como_rol):
    client = como_rol("cajero")

    r = client.post("/turnos/iniciar", json={"conteo_inicial": CONTEO})
    assert r.status_code == 200, r.text
    turno_id = r.json()["id"]

    r = client.post(f"/turnos/{turno_id}/cerrar", json={"conteo_final": CONTEO})
    assert r.status_code == 200, r.text
    body = r.json()

    # Sin ventas/gastos en el turno: diferencia = total_final - total_inicial = 0
    assert body["diferencia"] == 0.0

    r = client.get(f"/turnos/{turno_id}")
    assert r.json()["diferencia"] == 0.0


def test_cerrar_turno_con_faltante_persiste_diferencia_negativa(como_rol):
    client = como_rol("cajero")

    r = client.post("/turnos/iniciar", json={"conteo_inicial": CONTEO})  # $500 inicial
    turno_id = r.json()["id"]

    conteo_final_corto = {"denominaciones": [{"denominacion": 100, "cantidad": 4}]}  # $400
    r = client.post(f"/turnos/{turno_id}/cerrar", json={"conteo_final": conteo_final_corto})
    assert r.status_code == 200, r.text
    assert r.json()["diferencia"] == -100.0
