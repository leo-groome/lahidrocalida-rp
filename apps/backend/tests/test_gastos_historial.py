"""Historial y analítica de compras (SA PR4): total del filtro calculado en servidor,
filtro por categoría sin inflar la suma, analítica por proveedor/artículo y alerta
de días sin compras."""

from datetime import datetime, timedelta

from app.models import Articulo, CategoriaArticulo, Gasto, GastoDetalle, Proveedor
from app.utils.timezone import MEXICO_TZ, jornada_actual

DIA = "2026-10-16"
SIGUIENTE = "2026-10-17"


def _mx(dia: str, hora: int, minuto: int = 0) -> datetime:
    y, m, d = map(int, dia.split("-"))
    return datetime(y, m, d, hora, minuto, tzinfo=MEXICO_TZ)


def _gasto(db, seed, ts, total, tipo="directo", proveedor=None, lineas=()):
    g = Gasto(
        proveedor_id=proveedor.id if proveedor else None,
        tipo_gasto=tipo,
        metodo_pago="efectivo",
        subtotal=total,
        total=total,
        fecha_gasto=ts,
        sucursal_id=seed["sucursal"].id,
    )
    db.add(g)
    db.flush()
    for articulo, cantidad, precio in lineas:
        db.add(
            GastoDetalle(
                gasto_id=g.id,
                articulo_id=articulo.id,
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal_linea=cantidad * precio,
            )
        )
    db.commit()
    return g


def _catalogo(db):
    cat = CategoriaArticulo(nombre="lacteos")
    otra = CategoriaArticulo(nombre="carnes")
    db.add_all([cat, otra])
    db.flush()
    leche = Articulo(nombre="Leche", unidad="lt", categoria_id=cat.id, costo_estandar=20)
    crema = Articulo(nombre="Crema", unidad="lt", categoria_id=cat.id, costo_estandar=30)
    res = Articulo(nombre="Res", unidad="kg", categoria_id=otra.id, costo_estandar=150)
    db.add_all([leche, crema, res])
    db.commit()
    return cat, leche, crema, res


def test_suma_total_es_numero_y_cubre_todo_el_filtro(como_rol, seed, db_session):
    for i in range(3):
        _gasto(db_session, seed, _mx(DIA, 10 + i), 100)

    r = como_rol("administrador").get(
        f"/gastos/?fecha_inicio={DIA}&fecha_fin={DIA}&page=1&page_size=2"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == 2  # paginado
    assert body["total"] == 3
    assert body["suma_total"] == 300  # todo el filtro, no solo la página


def test_suma_total_con_categoria_no_se_infla_por_lineas(como_rol, seed, db_session):
    cat, leche, crema, res = _catalogo(db_session)
    # 1 gasto de $100 con DOS líneas de lacteos: el join las duplica, la suma no.
    _gasto(db_session, seed, _mx(DIA, 11), 100, lineas=[(leche, 2, 20), (crema, 2, 30)])
    _gasto(db_session, seed, _mx(DIA, 12), 500, lineas=[(res, 1, 500)])

    r = como_rol("administrador").get(f"/gastos/?categoria_id={cat.id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    assert body["suma_total"] == 100


def test_filtro_por_jornada_incluye_madrugada(como_rol, seed, db_session):
    _gasto(db_session, seed, _mx(DIA, 23, 50), 40)
    _gasto(db_session, seed, _mx(SIGUIENTE, 0, 20), 60)  # misma jornada del 16
    _gasto(db_session, seed, _mx(SIGUIENTE, 15, 0), 999)  # jornada del 17

    r = como_rol("administrador").get(f"/gastos/?fecha_inicio={DIA}&fecha_fin={DIA}")
    assert r.json()["suma_total"] == 100


def test_fecha_invalida_da_400(como_rol):
    r = como_rol("administrador").get("/gastos/?fecha_inicio=no-es-fecha")
    assert r.status_code == 400


def test_analitica_por_proveedor_y_articulo(como_rol, seed, db_session):
    cat, leche, crema, res = _catalogo(db_session)
    prov = Proveedor(nombre="Lala", sucursal_id=seed["sucursal"].id)
    db_session.add(prov)
    db_session.commit()
    _gasto(db_session, seed, _mx(DIA, 11), 100, proveedor=prov, lineas=[(leche, 5, 20)])
    _gasto(db_session, seed, _mx(DIA, 12), 60, proveedor=prov, lineas=[(leche, 3, 20)])
    _gasto(db_session, seed, _mx(DIA, 13), 900, tipo="nomina")

    r = como_rol("administrador").get(
        f"/gastos/analiticas/resumen?fecha_inicio={DIA}&fecha_fin={DIA}"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["por_proveedor"] == [
        {"id": prov.id, "nombre": "Lala", "total": 160.0, "compras": 2}
    ]  # nómina no tiene proveedor
    assert len(body["por_articulo"]) == 1
    art = body["por_articulo"][0]
    assert (art["nombre"], art["cantidad"], art["total"], art["categoria"]) == (
        "Leche",
        8.0,
        160.0,
        "lacteos",
    )


def test_dias_sin_compras_ignora_nomina(como_rol, seed, db_session):
    hoy = jornada_actual()
    hace3 = datetime.combine(hoy - timedelta(days=3), datetime.min.time(), MEXICO_TZ).replace(
        hour=12
    )
    _gasto(db_session, seed, hace3, 50)
    _gasto(db_session, seed, datetime.now(MEXICO_TZ), 800, tipo="nomina")  # no cuenta

    r = como_rol("administrador").get(f"/admin/analytics?fecha_inicio={hoy}&fecha_fin={hoy}")
    assert r.status_code == 200, r.text
    assert r.json()["resumen"]["dias_sin_compras"] == 3


def test_dias_sin_compras_none_si_nunca_hubo(como_rol):
    hoy = jornada_actual()
    r = como_rol("administrador").get(f"/admin/analytics?fecha_inicio={hoy}&fecha_fin={hoy}")
    assert r.json()["resumen"]["dias_sin_compras"] is None


def test_analitica_exige_autenticacion_de_rol_admin_para_dashboard(como_rol):
    hoy = jornada_actual()
    r = como_rol("mesero").get(f"/admin/analytics?fecha_inicio={hoy}&fecha_fin={hoy}")
    assert r.status_code == 403
