"""Analíticas de admin: el "día" es la jornada 05:00→05:00 hora México y la venta
se fecha por `fecha_pago` (SA PR1). Antes agrupaban por día UTC: lo vendido
después de las 18:00 locales caía en el día siguiente."""

from datetime import datetime

from app.models import ArticuloPedido, Gasto, Pedido
from app.utils.timezone import MEXICO_TZ

DIA = "2026-10-16"
SIGUIENTE = "2026-10-17"


def _mx(dia: str, hora: int, minuto: int = 0) -> datetime:
    y, m, d = map(int, dia.split("-"))
    return datetime(y, m, d, hora, minuto, tzinfo=MEXICO_TZ)


def _pagado(db, seed, ts, total=100, metodo="efectivo", articulos=(), n=[0]):
    n[0] += 1
    p = Pedido(
        numero_display=str(n[0]),
        total=total,
        estado="pagado",
        tipo_orden="aqui",
        metodo_pago=metodo,
        sucursal_id=seed["sucursal"].id,
        usuario_id=seed["usuario"].id,
        fecha_creacion=ts,
        fecha_pago=ts,
    )
    db.add(p)
    db.flush()
    for platillo_id, cantidad, precio_cobrado in articulos:
        db.add(
            ArticuloPedido(
                pedido_id=p.id,
                platillo_id=platillo_id,
                cantidad=cantidad,
                precio_cobrado=precio_cobrado,
                estado_item="entregado",
            )
        )
    db.commit()
    return p


def _dia(timeline, fecha):
    return next(d for d in timeline if d["fecha"] == fecha)


def test_venta_de_medianoche_cuenta_en_la_jornada_anterior(como_rol, seed, db_session):
    _pagado(db_session, seed, _mx(DIA, 23, 50), total=200)
    _pagado(db_session, seed, _mx(SIGUIENTE, 0, 20), total=300)  # misma jornada (del 16)
    _pagado(db_session, seed, _mx(SIGUIENTE, 15, 0), total=50)  # jornada del 17

    r = como_rol("administrador").get(
        f"/admin/analytics?fecha_inicio={DIA}&fecha_fin={SIGUIENTE}"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert _dia(body["timeline"], DIA)["ventas"] == 500
    assert _dia(body["timeline"], DIA)["pedidos"] == 2
    assert _dia(body["timeline"], SIGUIENTE)["ventas"] == 50
    assert body["resumen"]["total_ventas"] == 550


def test_hoy_no_incluye_la_noche_anterior(como_rol, seed, db_session):
    # Vendido a las 22:00 del 16 → pertenece al 16 aunque UTC ya sea día 17.
    _pagado(db_session, seed, _mx(DIA, 22, 0), total=999)

    r = como_rol("administrador").get(
        f"/admin/analytics?fecha_inicio={SIGUIENTE}&fecha_fin={SIGUIENTE}"
    )
    assert r.status_code == 200
    assert r.json()["resumen"]["total_ventas"] == 0


def test_dinero_por_platillo_no_multiplica_la_cantidad(como_rol, seed, db_session):
    platillo = seed["platillos"][0]
    # 3 piezas, precio_cobrado ya es el total de la línea ($150).
    _pagado(db_session, seed, _mx(DIA, 15), total=150, articulos=[(platillo.id, 3, 150)])

    r = como_rol("administrador").get(
        f"/admin/analytics/advanced?fecha_inicio={DIA}&fecha_fin={DIA}"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    top = next(p for p in body["top_platillos"] if p["nombre"] == platillo.nombre)
    assert top["cantidad"] == 3
    assert top["total"] == 150
    assert sum(c["total"] for c in body["ventas_categoria"]) == 150


def test_ventas_por_hora_en_hora_local_ordenadas_por_jornada(como_rol, seed, db_session):
    _pagado(db_session, seed, _mx(DIA, 14, 10), total=10)
    _pagado(db_session, seed, _mx(DIA, 23, 5), total=20)
    _pagado(db_session, seed, _mx(SIGUIENTE, 0, 15), total=30)

    r = como_rol("administrador").get(
        f"/admin/analytics/advanced?fecha_inicio={DIA}&fecha_fin={DIA}"
    )
    horas = [h["hora"] for h in r.json()["ventas_por_hora"]]
    assert horas == [14, 23, 0]


def test_proyeccion_en_espanol(como_rol, seed):
    r = como_rol("administrador").get(
        f"/admin/analytics/advanced?fecha_inicio={DIA}&fecha_fin={DIA}"
    )
    dias = [d["dia"] for d in r.json()["proyeccion_ia"]["proximos_7_dias"]]
    assert dias == ["Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def test_filtro_transferencia_no_rompe_gastos(como_rol, seed, db_session):
    _pagado(db_session, seed, _mx(DIA, 15), total=80, metodo="transferencia")
    db_session.add(
        Gasto(
            proveedor_id=None,
            tipo_gasto="directo",
            metodo_pago="efectivo",
            subtotal=40,
            total=40,
            fecha_gasto=_mx(DIA, 11),
            sucursal_id=seed["sucursal"].id,
        )
    )
    db_session.commit()

    r = como_rol("administrador").get(
        f"/admin/analytics?fecha_inicio={DIA}&fecha_fin={DIA}&metodo_pago=transferencia"
    )
    assert r.status_code == 200, r.text
    resumen = r.json()["resumen"]
    assert resumen["total_ventas"] == 80
    assert resumen["total_gastos"] == 40


def test_rango_invalido_422_y_formato_400(como_rol):
    admin = como_rol("administrador")
    r = admin.get(f"/admin/analytics?fecha_inicio={SIGUIENTE}&fecha_fin={DIA}")
    assert r.status_code == 422
    r = admin.get("/admin/analytics?fecha_inicio=hoy&fecha_fin=mañana")
    assert r.status_code == 400
    r = admin.get("/admin/analytics?fecha_inicio=2020-01-01&fecha_fin=2026-10-16")
    assert r.status_code == 422


def test_semana_hidrocalida_es_martes_a_domingo():
    from datetime import date

    from app.utils.timezone import semana_hidrocalida

    assert semana_hidrocalida(date(2026, 10, 17)) == (date(2026, 10, 13), date(2026, 10, 18))
    # El lunes (cerrado) cae en la semana que terminó el domingo anterior.
    assert semana_hidrocalida(date(2026, 10, 12)) == (date(2026, 10, 6), date(2026, 10, 11))
