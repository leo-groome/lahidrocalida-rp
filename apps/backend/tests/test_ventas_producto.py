"""Reporte de ventas por producto (SA PR3) y KPIs de dinero del dashboard."""

from datetime import datetime

from app.models import ArticuloPedido, Pedido, Sucursal
from app.utils.timezone import MEXICO_TZ

DIA = "2026-10-16"
SIG = "2026-10-17"
RANGO = f"fecha_inicio={DIA}&fecha_fin={SIG}"


def _mx(dia: str, hora: int, minuto: int = 0) -> datetime:
    y, m, d = map(int, dia.split("-"))
    return datetime(y, m, d, hora, minuto, tzinfo=MEXICO_TZ)


_n = [0]


def _pedido(db, seed, ts, total, estado="pagado", metodo="efectivo", lineas=(), **kw):
    _n[0] += 1
    p = Pedido(
        numero_display=str(_n[0]),
        total=total,
        estado=estado,
        tipo_orden=kw.pop("tipo_orden", "aqui"),
        metodo_pago=metodo,
        sucursal_id=kw.pop("sucursal_id", seed["sucursal"].id),
        usuario_id=seed["usuario"].id,
        fecha_creacion=ts,
        fecha_pago=ts if estado in ("pagado", "entregado_repartidor") else None,
        **kw,
    )
    db.add(p)
    db.flush()
    for platillo, cantidad, precio in lineas:
        db.add(
            ArticuloPedido(
                pedido_id=p.id,
                platillo_id=platillo.id,
                cantidad=cantidad,
                precio_cobrado=precio,
                estado_item="entregado",
            )
        )
    db.commit()
    return p


def _producto(body, platillo):
    return next((p for p in body["productos"] if p["platillo_id"] == platillo.id), None)


def test_unidades_e_ingreso_por_producto_y_por_dia(como_rol, seed, db_session):
    a, b = seed["platillos"][0], seed["platillos"][1]
    _pedido(db_session, seed, _mx(DIA, 15), 300, lineas=[(a, 3, 300)])
    _pedido(db_session, seed, _mx(SIG, 0, 20), 100, lineas=[(a, 1, 100)])  # jornada del 16
    _pedido(db_session, seed, _mx(SIG, 15), 100, lineas=[(b, 1, 100)])  # jornada del 17

    r = como_rol("administrador").get(f"/admin/analytics/productos?{RANGO}")
    assert r.status_code == 200, r.text
    body = r.json()

    pa = _producto(body, a)
    assert pa["unidades"] == 4 and pa["ingreso"] == 400
    assert pa["precio_promedio"] == 100
    assert pa["por_dia"][DIA] == {"unidades": 4, "ingreso": 400}
    assert SIG not in pa["por_dia"]
    assert _producto(body, b)["por_dia"][SIG]["unidades"] == 1
    assert body["dias"] == [DIA, SIG]
    assert body["totales"] == {"unidades": 5, "ingreso": 500}
    assert sum(c["porcentaje"] for c in body["categorias"]) == 100


def test_no_cuenta_pendientes_cancelados_ni_articulos_eliminados(como_rol, seed, db_session):
    a = seed["platillos"][0]
    _pedido(db_session, seed, _mx(DIA, 15), 100, lineas=[(a, 1, 100)])
    _pedido(db_session, seed, _mx(DIA, 16), 100, estado="entregado", lineas=[(a, 1, 100)])
    _pedido(db_session, seed, _mx(DIA, 17), 100, estado="cancelado", lineas=[(a, 1, 100)])
    _pedido(db_session, seed, _mx(DIA, 18), 0, lineas=[(a, 0, 0)])  # artículo eliminado

    body = como_rol("administrador").get(f"/admin/analytics/productos?{RANGO}").json()
    assert _producto(body, a)["unidades"] == 1


def test_uber_eats_cuenta_como_venta_de_producto(como_rol, seed, db_session):
    a = seed["platillos"][0]
    _pedido(
        db_session,
        seed,
        _mx(DIA, 19),
        250,
        estado="entregado_repartidor",
        metodo=None,
        tipo_orden="uber_eats",
        lineas=[(a, 2, 250)],
    )
    body = como_rol("administrador").get(f"/admin/analytics/productos?{RANGO}").json()
    assert _producto(body, a)["unidades"] == 2


def test_cuenta_dividida_por_articulos_no_se_duplica(como_rol, seed, db_session):
    a = seed["platillos"][0]
    padre = _pedido(
        db_session, seed, _mx(DIA, 20), 200, estado="dividido", metodo=None, lineas=[(a, 2, 200)]
    )
    for i in range(2):  # dos hijas con 1 pieza cada una, ambas pagadas
        _pedido(
            db_session, seed, _mx(DIA, 21, i), 100, lineas=[(a, 1, 100)], parent_pedido_id=padre.id
        )

    body = como_rol("administrador").get(f"/admin/analytics/productos?{RANGO}").json()
    p = _producto(body, a)
    assert p["unidades"] == 2 and p["ingreso"] == 200  # no 4 / 400


def test_cuenta_dividida_por_montos_atribuye_articulos_al_padre_cuando_se_liquida(
    como_rol, seed, db_session
):
    a = seed["platillos"][0]
    padre = _pedido(
        db_session, seed, _mx(DIA, 20), 200, estado="dividido", metodo=None, lineas=[(a, 2, 200)]
    )
    _pedido(db_session, seed, _mx(DIA, 21), 100, parent_pedido_id=padre.id)  # hija sin artículos
    admin = como_rol("administrador")

    # Mientras falte una hija por pagar no hay venta que atribuir.
    pendiente = _pedido(
        db_session,
        seed,
        None,
        100,
        estado="cuenta_solicitada",
        metodo=None,
        parent_pedido_id=padre.id,
    )
    assert _producto(admin.get(f"/admin/analytics/productos?{RANGO}").json(), a) is None

    pendiente.estado = "pagado"
    pendiente.metodo_pago = "tarjeta"
    pendiente.fecha_pago = _mx(SIG, 0, 10)  # último pago pasada la medianoche
    db_session.commit()

    p = _producto(admin.get(f"/admin/analytics/productos?{RANGO}").json(), a)
    assert p["unidades"] == 2 and p["ingreso"] == 200
    assert p["por_dia"][DIA]["unidades"] == 2  # 00:10 sigue siendo la jornada del 16


def test_filtro_categoria_y_aislamiento_por_sucursal(como_rol, seed, db_session):
    a, b = seed["platillos"][0], seed["platillos"][1]
    b.categoria = "Tamales"
    otra = Sucursal(nombre="Otra")
    db_session.add(otra)
    db_session.flush()
    _pedido(db_session, seed, _mx(DIA, 15), 100, lineas=[(a, 1, 100)])
    _pedido(db_session, seed, _mx(DIA, 15), 100, lineas=[(b, 1, 100)])
    _pedido(db_session, seed, _mx(DIA, 15), 900, lineas=[(a, 9, 900)], sucursal_id=otra.id)

    admin = como_rol("administrador")
    todo = admin.get(f"/admin/analytics/productos?{RANGO}").json()
    assert _producto(todo, a)["unidades"] == 1  # nada de la otra sucursal
    solo = admin.get(f"/admin/analytics/productos?{RANGO}&categoria=Tamales").json()
    assert [p["platillo_id"] for p in solo["productos"]] == [b.id]


def test_productos_rango_invalido_y_solo_admin(como_rol):
    assert (
        como_rol("administrador")
        .get(f"/admin/analytics/productos?fecha_inicio={SIG}&fecha_fin={DIA}")
        .status_code
        == 422
    )
    assert como_rol("cajero").get(f"/admin/analytics/productos?{RANGO}").status_code == 403


def test_kpis_de_dinero_metodos_propinas_uber_y_periodo_anterior(como_rol, seed, db_session):
    _pedido(db_session, seed, _mx(DIA, 15), 300, metodo="efectivo", propina_efectivo=20)
    _pedido(db_session, seed, _mx(DIA, 16), 200, metodo="tarjeta", propina_tarjeta=15)
    _pedido(db_session, seed, _mx(DIA, 17), 50, metodo="transferencia")
    _pedido(
        db_session,
        seed,
        _mx(DIA, 18),
        120,
        estado="entregado_repartidor",
        metodo=None,
        tipo_orden="uber_eats",
    )
    _pedido(db_session, seed, _mx("2026-10-14", 15), 400)  # periodo anterior (2 días antes)

    body = como_rol("administrador").get(f"/admin/analytics?{RANGO}").json()
    r = body["resumen"]
    assert r["total_ventas"] == 550  # Uber no se mezcla con lo cobrado en Caja
    assert r["por_metodo"]["efectivo"] == {"total": 300.0, "pedidos": 1}
    assert r["por_metodo"]["tarjeta"]["total"] == 200
    assert r["por_metodo"]["transferencia"]["total"] == 50
    assert r["uber"] == {"total": 120.0, "pedidos": 1}
    assert (r["propinas_efectivo"], r["propinas_tarjeta"]) == (20, 15)
    assert body["anterior"]["total_ventas"] == 400
    assert body["anterior"]["fin"] == "2026-10-15"
    dia = next(d for d in body["timeline"] if d["fecha"] == DIA)
    assert (dia["efectivo"], dia["tarjeta"], dia["transferencia"]) == (300, 200, 50)


def test_top_platillos_del_resumen_coincide_con_el_reporte_por_producto(como_rol, seed, db_session):
    """El Resumen y la pestaña "Ventas por producto" no deben discrepar: el top incluye
    Uber, y la categoría también."""
    a = seed["platillos"][0]
    _pedido(db_session, seed, _mx(DIA, 15), 100, lineas=[(a, 1, 100)])
    _pedido(
        db_session,
        seed,
        _mx(DIA, 19),
        200,
        estado="entregado_repartidor",
        metodo=None,
        tipo_orden="uber_eats",
        lineas=[(a, 2, 200)],
    )
    admin = como_rol("administrador")
    adv = admin.get(f"/admin/analytics/advanced?{RANGO}").json()
    assert adv["top_platillos"][0]["cantidad"] == 3
    assert adv["top_platillos"][0]["total"] == 300
    assert adv["ventas_categoria"][0]["total"] == 300
    # Con filtro de pago se mantiene la consulta directa (solo lo cobrado con ese método).
    ef = admin.get(f"/admin/analytics/advanced?{RANGO}&metodo_pago=efectivo").json()
    assert ef["top_platillos"][0]["cantidad"] == 1
