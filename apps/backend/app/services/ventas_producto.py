"""Reporte de ventas por producto y por jornada (SA PR3).

Responde "¿cuántos pozoles verdes / tamales vendí, y qué día?". Reglas de qué cuenta
como venta de un artículo:

1. Pedidos `pagado` y Uber Eats `entregado_repartidor` (el dinero llega por depósito,
   pero es venta). Fecha = `fecha_pago` (respaldo `fecha_creacion`).
2. Cuenta dividida **por artículos**: cuentan las cuentas hijas (tienen sus propios
   artículos); el padre `dividido` NO cuenta, o se duplicaría.
3. Cuenta dividida **por montos**: las hijas no tienen artículos, así que los artículos
   se atribuyen al padre `dividido` — solo cuando todas sus hijas vigentes ya están
   pagadas — con la fecha del último pago de las hijas.
4. Artículos eliminados del pedido (cantidad 0) no cuentan.

`precio_cobrado` ya es el total de la línea (precio × cantidad): se suma tal cual.
El "día" es la jornada 05:00→05:00 hora México (`jornada_de`).
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.domain.estados import TIPO_ORDEN_UBER, EstadoPedido
from app.models import ArticuloPedido, Pedido, Platillo
from app.utils.timezone import jornada_de, rango_jornadas, to_mexico_aware

# Una venta se fecha cuando se cobra (o se entrega al repartidor en Uber).
VENTA_TS = func.coalesce(Pedido.fecha_pago, Pedido.fecha_creacion)


def _es_venta():
    return or_(
        Pedido.estado == EstadoPedido.PAGADO,
        and_(
            Pedido.tipo_orden == TIPO_ORDEN_UBER,
            Pedido.estado == EstadoPedido.ENTREGADO_REPARTIDOR,
        ),
    )


def _lineas(db: Session, *filtros) -> list:
    return (
        db.query(
            ArticuloPedido.platillo_id,
            Platillo.nombre,
            Platillo.categoria,
            ArticuloPedido.cantidad,
            ArticuloPedido.precio_cobrado,
            VENTA_TS.label("ts"),
        )
        .join(Pedido, ArticuloPedido.pedido_id == Pedido.id)
        .join(Platillo, ArticuloPedido.platillo_id == Platillo.id)
        .filter(ArticuloPedido.cantidad > 0, *filtros)
        .all()
    )


def _padres_dividido_por_monto(
    db: Session, sucursal_id: int, inicio_dt: datetime, fin_dt: datetime
) -> Dict[int, datetime]:
    """{padre_id: fecha del último pago de sus hijas} de las cuentas divididas por
    montos ya liquidadas por completo cuyo último pago cae en el rango."""
    padres_candidatos = {
        pid
        for (pid,) in db.query(Pedido.parent_pedido_id)
        .filter(
            Pedido.sucursal_id == sucursal_id,
            Pedido.parent_pedido_id.isnot(None),
            Pedido.estado == EstadoPedido.PAGADO,
            VENTA_TS >= inicio_dt,
            VENTA_TS < fin_dt,
        )
        .distinct()
    }
    if not padres_candidatos:
        return {}

    padres_dividido = {
        pid
        for (pid,) in db.query(Pedido.id).filter(
            Pedido.id.in_(padres_candidatos), Pedido.estado == EstadoPedido.DIVIDIDO
        )
    }
    if not padres_dividido:
        return {}

    hijas = (
        db.query(Pedido.id, Pedido.parent_pedido_id, Pedido.estado, VENTA_TS.label("ts"))
        .filter(Pedido.parent_pedido_id.in_(padres_dividido))
        .all()
    )
    hijas_con_articulos = {
        pid
        for (pid,) in db.query(ArticuloPedido.pedido_id)
        .filter(ArticuloPedido.pedido_id.in_([h.id for h in hijas]), ArticuloPedido.cantidad > 0)
        .distinct()
    }

    por_padre: Dict[int, list] = defaultdict(list)
    for h in hijas:
        por_padre[h.parent_pedido_id].append(h)

    resultado: Dict[int, datetime] = {}
    for padre_id, hs in por_padre.items():
        vigentes = [h for h in hs if h.estado != EstadoPedido.CANCELADO]
        if not vigentes or any(h.id in hijas_con_articulos for h in hs):
            continue  # split por artículos: cuentan las hijas, no el padre
        if any(h.estado != EstadoPedido.PAGADO for h in vigentes):
            continue  # aún sin liquidar
        ultimo_pago = max(to_mexico_aware(h.ts) for h in vigentes)
        if inicio_dt <= ultimo_pago < fin_dt:
            resultado[padre_id] = ultimo_pago
    return resultado


def ventas_por_producto(
    db: Session,
    sucursal_id: int,
    inicio: date,
    fin: date,
    categoria: Optional[str] = None,
) -> Dict[str, Any]:
    inicio_dt, fin_dt = rango_jornadas(inicio, fin)

    lineas = _lineas(
        db,
        Pedido.sucursal_id == sucursal_id,
        VENTA_TS >= inicio_dt,
        VENTA_TS < fin_dt,
        _es_venta(),
    )
    # (platillo_id, nombre, categoria, cantidad, precio_cobrado, ts)
    filas: List[tuple] = [tuple(linea) for linea in lineas]

    for padre_id, ts_pago in _padres_dividido_por_monto(db, sucursal_id, inicio_dt, fin_dt).items():
        for linea in _lineas(db, ArticuloPedido.pedido_id == padre_id):
            filas.append((*tuple(linea)[:5], ts_pago))

    productos: Dict[int, Dict[str, Any]] = {}
    for platillo_id, nombre, cat, cantidad, precio_cobrado, ts in filas:
        if categoria and cat != categoria:
            continue
        p = productos.setdefault(
            platillo_id,
            {
                "platillo_id": platillo_id,
                "nombre": nombre.strip(),
                "categoria": cat,
                "unidades": 0,
                "ingreso": 0.0,
                "por_dia": {},
            },
        )
        dia = jornada_de(ts).isoformat()
        d = p["por_dia"].setdefault(dia, {"unidades": 0, "ingreso": 0.0})
        for destino in (p, d):
            destino["unidades"] += int(cantidad)
            destino["ingreso"] += float(precio_cobrado or 0)

    lista = sorted(productos.values(), key=lambda p: (-p["unidades"], p["nombre"]))
    total_unidades = sum(p["unidades"] for p in lista)
    total_ingreso = sum(p["ingreso"] for p in lista)
    for p in lista:
        p["ingreso"] = round(p["ingreso"], 2)
        p["precio_promedio"] = round(p["ingreso"] / p["unidades"], 2) if p["unidades"] else 0.0
        for d in p["por_dia"].values():
            d["ingreso"] = round(d["ingreso"], 2)

    por_categoria: Dict[str, Dict[str, Any]] = {}
    for p in lista:
        c = por_categoria.setdefault(
            p["categoria"], {"categoria": p["categoria"], "unidades": 0, "ingreso": 0.0}
        )
        c["unidades"] += p["unidades"]
        c["ingreso"] += p["ingreso"]
    categorias = sorted(por_categoria.values(), key=lambda c: -c["ingreso"])
    for c in categorias:
        c["ingreso"] = round(c["ingreso"], 2)
        c["porcentaje"] = round(c["ingreso"] / total_ingreso * 100, 1) if total_ingreso else 0.0

    dias = [(inicio + timedelta(days=i)).isoformat() for i in range((fin - inicio).days + 1)]
    return {
        "periodo": {"inicio": inicio.isoformat(), "fin": fin.isoformat()},
        "dias": dias,
        "productos": lista,
        "categorias": categorias,
        "totales": {"unidades": total_unidades, "ingreso": round(total_ingreso, 2)},
    }
