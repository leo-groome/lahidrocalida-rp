"""Configuración de sueldo y horario por empleado (base del cálculo de nómina)."""

from datetime import date, timedelta
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import verificar_pin_admin
from app.db.session import get_db
from app.deps import obtener_turno_activo, require_roles
from app.domain.estados import MAX_HORAS_JORNADA
from app.models import (
    AutorizacionPin,
    EmpleadoPago,
    Gasto,
    HorarioEmpleado,
    NominaDetalle,
    NominaLinea,
    NominaPeriodo,
    RegistroAsistencia,
    Usuario,
    get_local_datetime,
)
from app.schemas import (
    DiaNomina,
    EmpleadoNominaResponse,
    EmpleadoPagoResponse,
    EmpleadoPagoUpdate,
    HorarioDia,
    HorarioUpdate,
    LineaNominaResponse,
    LineaNominaUpdate,
    PagarNominaRequest,
    PeriodoNominaCreate,
    PeriodoNominaResponse,
)
from app.services.nomina import (
    Reglas,
    calcular_montos,
    dias_y_extras,
    faltas,
    horas_por_jornada,
    total_linea,
)
from app.utils.timezone import (
    jornada_actual,
    jornada_de,
    rango_jornadas,
    semana_hidrocalida,
    to_mexico_aware,
)

router = APIRouter(prefix="/nomina", tags=["nomina"])

# Los administradores no checan asistencia: no entran a nómina.
ROLES_NOMINA = ("cajero", "cocina", "mesero", "compras")


def _empleado(db: Session, usuario_id: int, sucursal_id: int) -> Usuario:
    usuario = (
        db.query(Usuario)
        .filter(
            Usuario.id == usuario_id,
            Usuario.sucursal_id == sucursal_id,
            Usuario.activo == True,  # noqa: E712
            Usuario.rol.in_(ROLES_NOMINA),
        )
        .first()
    )
    if usuario is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return usuario


@router.get("/empleados", response_model=List[EmpleadoNominaResponse])
def list_empleados(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    usuarios = (
        db.query(Usuario)
        .filter(
            Usuario.sucursal_id == current_user.sucursal_id,
            Usuario.activo == True,  # noqa: E712
            Usuario.rol.in_(ROLES_NOMINA),
        )
        .order_by(Usuario.nombre)
        .all()
    )
    ids = [u.id for u in usuarios]
    pagos = {
        p.usuario_id: p
        for p in db.query(EmpleadoPago).filter(
            EmpleadoPago.sucursal_id == current_user.sucursal_id, EmpleadoPago.usuario_id.in_(ids)
        )
    }
    horarios: dict[int, list[HorarioEmpleado]] = {}
    for h in (
        db.query(HorarioEmpleado)
        .filter(
            HorarioEmpleado.sucursal_id == current_user.sucursal_id,
            HorarioEmpleado.usuario_id.in_(ids),
        )
        .order_by(HorarioEmpleado.dia_semana)
    ):
        horarios.setdefault(h.usuario_id, []).append(h)
    return [
        EmpleadoNominaResponse(
            usuario_id=u.id,
            nombre=u.nombre,
            rol=u.rol,
            pago=EmpleadoPagoResponse.model_validate(pagos[u.id]) if u.id in pagos else None,
            horario=[HorarioDia.model_validate(h) for h in horarios.get(u.id, [])],
        )
        for u in usuarios
    ]


@router.put("/empleados/{usuario_id}/pago", response_model=EmpleadoPagoResponse)
def set_pago(
    usuario_id: int,
    data: EmpleadoPagoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    _empleado(db, usuario_id, current_user.sucursal_id)
    pago = db.query(EmpleadoPago).filter(EmpleadoPago.usuario_id == usuario_id).first()
    if pago is None:
        pago = EmpleadoPago(usuario_id=usuario_id, sucursal_id=current_user.sucursal_id)
        db.add(pago)
    for campo, valor in data.model_dump().items():
        setattr(pago, campo, valor)
    db.commit()
    db.refresh(pago)
    return pago


@router.put("/empleados/{usuario_id}/horario", response_model=List[HorarioDia])
def set_horario(
    usuario_id: int,
    data: HorarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    """Reemplaza el horario semanal completo (los días que no vengan quedan de descanso)."""
    _empleado(db, usuario_id, current_user.sucursal_id)
    db.query(HorarioEmpleado).filter(HorarioEmpleado.usuario_id == usuario_id).delete()
    filas = [
        HorarioEmpleado(
            usuario_id=usuario_id, sucursal_id=current_user.sucursal_id, **d.model_dump()
        )
        for d in sorted(data.dias, key=lambda d: d.dia_semana)
    ]
    db.add_all(filas)
    db.commit()
    return [HorarioDia.model_validate(f) for f in filas]


# ===== Nómina semanal =====

DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def _reglas(pago: EmpleadoPago) -> Reglas:
    return Reglas(
        tarifa_hora=Decimal(pago.tarifa_hora),
        tarifa_hora_extra=Decimal(pago.tarifa_hora_extra),
        horas_jornada=Decimal(pago.horas_jornada),
    )


def _semana(fecha: date) -> tuple[date, date]:
    """Martes a lunes de la semana operativa que contiene `fecha`."""
    martes, _ = semana_hidrocalida(fecha)
    return martes, martes + timedelta(days=6)


def _empleados_activos(db: Session, sucursal_id: int) -> list[Usuario]:
    return (
        db.query(Usuario)
        .filter(
            Usuario.sucursal_id == sucursal_id,
            Usuario.activo == True,  # noqa: E712
            Usuario.rol.in_(ROLES_NOMINA),
        )
        .order_by(Usuario.nombre)
        .all()
    )


def _dias_horario(db: Session, ids: list[int]) -> dict[int, set[int]]:
    """Días de la semana (0=lunes) que trabaja cada empleado según su horario."""
    dias: dict[int, set[int]] = {}
    for uid, dia in db.query(HorarioEmpleado.usuario_id, HorarioEmpleado.dia_semana).filter(
        HorarioEmpleado.usuario_id.in_(ids)
    ):
        dias.setdefault(uid, set()).add(dia)
    return dias


def _ultimo_dia(periodo: NominaPeriodo, dias_semana: set[int]) -> date:
    """Último día del periodo que le toca trabajar; sin horario, el domingo."""
    if not dias_semana:
        return periodo.fecha_inicio + timedelta(days=5)
    fechas = (periodo.fecha_inicio + timedelta(days=i) for i in range(7))
    return max(f for f in fechas if f.weekday() in dias_semana)


def _sin_salida_por_usuario(
    db: Session, sucursal_id: int, inicio: date, fin: date
) -> dict[int, int]:
    desde, hasta = rango_jornadas(inicio, fin)
    return dict(
        db.query(RegistroAsistencia.usuario_id, func.count(RegistroAsistencia.id))
        .join(Usuario, Usuario.id == RegistroAsistencia.usuario_id)
        .filter(
            Usuario.sucursal_id == sucursal_id,
            RegistroAsistencia.fecha_salida.is_(None),
            RegistroAsistencia.fecha_entrada >= desde,
            RegistroAsistencia.fecha_entrada < hasta,
        )
        .group_by(RegistroAsistencia.usuario_id)
        .all()
    )


def _recalcular(db: Session, periodo: NominaPeriodo, forzar: bool = False) -> None:
    """Crea/actualiza las líneas desde asistencia.

    Conserva bonos, descuentos, método y notas. Las líneas ya pagadas no se tocan; las
    que el admin corrigió a mano conservan sus horas salvo que `forzar`.
    """
    sucursal_id = periodo.sucursal_id
    pagos = {
        p.usuario_id: p
        for p in db.query(EmpleadoPago).filter(EmpleadoPago.sucursal_id == sucursal_id)
    }
    empleados = [u for u in _empleados_activos(db, sucursal_id) if u.id in pagos]
    ids = [u.id for u in empleados]
    desde, hasta = rango_jornadas(periodo.fecha_inicio, periodo.fecha_fin)
    registros: dict[int, list[tuple]] = {}
    for uid, entrada, salida in db.query(
        RegistroAsistencia.usuario_id,
        RegistroAsistencia.fecha_entrada,
        RegistroAsistencia.fecha_salida,
    ).filter(
        RegistroAsistencia.usuario_id.in_(ids),
        RegistroAsistencia.fecha_salida.isnot(None),
        RegistroAsistencia.requiere_revision == False,  # noqa: E712
        RegistroAsistencia.fecha_entrada >= desde,
        RegistroAsistencia.fecha_entrada < hasta,
    ):
        registros.setdefault(uid, []).append((entrada, salida))
    dias_horario = _dias_horario(db, ids)
    existentes = {ln.usuario_id: ln for ln in periodo.lineas}
    for u in empleados:
        linea = existentes.get(u.id)
        if linea is not None and linea.gasto_id is not None:
            continue
        reglas = _reglas(pagos[u.id])
        dias, extra, horas = dias_y_extras(
            horas_por_jornada(registros.get(u.id, [])), reglas.horas_jornada
        )
        if linea is None:
            linea = NominaLinea(usuario_id=u.id, bonos=Decimal(0), descuentos=Decimal(0))
            periodo.lineas.append(linea)
        if forzar:
            linea.horas_ajustadas = False
        if not linea.horas_ajustadas:
            linea.horas_trabajadas, linea.horas_extra = horas, extra
        linea.dias_esperados = len(dias_horario.get(u.id, ()))
        linea.dias_trabajados = dias
        linea.faltas = faltas(dias, linea.dias_esperados)
        _aplicar_montos(linea, reglas)
    db.flush()


def _aplicar_montos(linea: NominaLinea, reglas: Reglas) -> None:
    montos = calcular_montos(reglas, Decimal(linea.horas_trabajadas), Decimal(linea.horas_extra))
    linea.base, linea.extra_monto = montos.base, montos.extra_monto
    linea.total = total_linea(montos, Decimal(linea.bonos), Decimal(linea.descuentos))


def _bloqueo(ln: NominaLinea, ultimo: date, hoy: date, sin_salida: int) -> str | None:
    if ln.gasto_id is not None:
        return None
    if hoy < ultimo:
        return f"Se paga el {DIAS[ultimo.weekday()]} {ultimo:%d/%m}, su último día"
    if sin_salida:
        return f"Tiene {sin_salida} entrada(s) sin salida: pídele que checke salida o espera al cierre automático"
    return None


def _respuesta(db: Session, periodo: NominaPeriodo) -> PeriodoNominaResponse:
    sucursal_id = periodo.sucursal_id
    con_linea = {ln.usuario_id for ln in periodo.lineas}
    configurados = {
        uid
        for (uid,) in db.query(EmpleadoPago.usuario_id).filter(
            EmpleadoPago.sucursal_id == sucursal_id
        )
    }
    sin_configurar = (
        [
            u.nombre
            for u in _empleados_activos(db, sucursal_id)
            if u.id not in configurados and u.id not in con_linea
        ]
        if periodo.estado == "borrador"
        else []
    )
    lineas = sorted(periodo.lineas, key=lambda ln: ln.usuario.nombre.lower())
    ids = [ln.usuario_id for ln in lineas]
    desde, hasta = rango_jornadas(periodo.fecha_inicio, periodo.fecha_fin)
    automaticas = dict(
        db.query(RegistroAsistencia.usuario_id, func.count(RegistroAsistencia.id))
        .filter(
            RegistroAsistencia.usuario_id.in_(ids),
            RegistroAsistencia.cierre_automatico == True,  # noqa: E712
            RegistroAsistencia.fecha_entrada >= desde,
            RegistroAsistencia.fecha_entrada < hasta,
        )
        .group_by(RegistroAsistencia.usuario_id)
        .all()
    )
    sin_salida = _sin_salida_por_usuario(db, sucursal_id, periodo.fecha_inicio, periodo.fecha_fin)
    dias_por_usuario: dict[int, list[DiaNomina]] = {}
    for reg in (
        db.query(RegistroAsistencia)
        .filter(
            RegistroAsistencia.usuario_id.in_(ids),
            RegistroAsistencia.fecha_entrada >= desde,
            RegistroAsistencia.fecha_entrada < hasta,
        )
        .order_by(RegistroAsistencia.fecha_entrada)
    ):
        entrada = to_mexico_aware(reg.fecha_entrada)
        horas = Decimal(0)
        if reg.fecha_salida is not None:
            segundos = (to_mexico_aware(reg.fecha_salida) - entrada).total_seconds()
            horas = min(max(Decimal(str(segundos / 3600)), Decimal(0)), Decimal(MAX_HORAS_JORNADA))
        dias_por_usuario.setdefault(reg.usuario_id, []).append(
            DiaNomina(
                fecha=jornada_de(entrada),
                entrada=reg.fecha_entrada,
                salida=reg.fecha_salida,
                horas=horas.quantize(Decimal("0.01")),
                automatica=bool(reg.cierre_automatico),
                abierta=reg.fecha_salida is None,
            )
        )
    dias_horario = _dias_horario(db, ids)
    hoy = jornada_actual()
    return PeriodoNominaResponse(
        id=periodo.id,
        fecha_inicio=periodo.fecha_inicio,
        fecha_fin=periodo.fecha_fin,
        estado=periodo.estado,
        pagado_en=periodo.pagado_en,
        total=sum((Decimal(ln.total) for ln in lineas), Decimal(0)),
        pendientes_asistencia=sum(sin_salida.values()),
        sin_configurar=sin_configurar,
        lineas=[
            LineaNominaResponse(
                usuario_id=ln.usuario_id,
                nombre=ln.usuario.nombre,
                dias_esperados=ln.dias_esperados,
                dias_trabajados=ln.dias_trabajados,
                faltas=ln.faltas,
                horas_trabajadas=ln.horas_trabajadas,
                horas_extra=ln.horas_extra,
                base=ln.base,
                extra_monto=ln.extra_monto,
                bonos=ln.bonos,
                descuentos=ln.descuentos,
                total=ln.total,
                metodo_pago=ln.metodo_pago,
                sale_de_caja=ln.sale_de_caja,
                notas=ln.notas,
                pagada=ln.gasto_id is not None,
                dias=dias_por_usuario.get(ln.usuario_id, []),
                ultimo_dia=(ultimo := _ultimo_dia(periodo, dias_horario.get(ln.usuario_id, set()))),
                bloqueo=_bloqueo(ln, ultimo, hoy, sin_salida.get(ln.usuario_id, 0)),
                salidas_automaticas=automaticas.get(ln.usuario_id, 0),
            )
            for ln in lineas
        ],
    )


def _periodo(
    db: Session, periodo_id: int, sucursal_id: int, bloquear: bool = False
) -> NominaPeriodo:
    query = db.query(NominaPeriodo).filter(
        NominaPeriodo.id == periodo_id, NominaPeriodo.sucursal_id == sucursal_id
    )
    periodo = (query.with_for_update() if bloquear else query).first()
    if periodo is None:
        raise HTTPException(status_code=404, detail="Periodo no encontrado")
    return periodo


@router.post("/periodos", response_model=PeriodoNominaResponse)
def abrir_periodo(
    data: PeriodoNominaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    """Devuelve la nómina de la semana, calculada con la asistencia al momento (borrador)."""
    inicio, fin = _semana(data.fecha_inicio)
    periodo = (
        db.query(NominaPeriodo)
        .filter(
            NominaPeriodo.sucursal_id == current_user.sucursal_id,
            NominaPeriodo.fecha_inicio == inicio,
        )
        .with_for_update()
        .first()
    )
    if periodo is None:
        periodo = NominaPeriodo(
            sucursal_id=current_user.sucursal_id,
            fecha_inicio=inicio,
            fecha_fin=fin,
            estado="borrador",
        )
        db.add(periodo)
    if periodo.estado == "borrador":
        _recalcular(db, periodo)
        db.commit()
        db.refresh(periodo)
    return _respuesta(db, periodo)


@router.post("/periodos/{periodo_id}/recalcular", response_model=PeriodoNominaResponse)
def recalcular_periodo(
    periodo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    """Vuelve a leer la asistencia descartando las horas corregidas a mano (conserva bonos)."""
    periodo = _periodo(db, periodo_id, current_user.sucursal_id, bloquear=True)
    if periodo.estado != "borrador":
        raise HTTPException(status_code=409, detail="La nómina ya fue pagada")
    _recalcular(db, periodo, forzar=True)
    db.commit()
    db.refresh(periodo)
    return _respuesta(db, periodo)


@router.put("/periodos/{periodo_id}/lineas/{usuario_id}", response_model=PeriodoNominaResponse)
def editar_linea(
    periodo_id: int,
    usuario_id: int,
    data: LineaNominaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    periodo = _periodo(db, periodo_id, current_user.sucursal_id, bloquear=True)
    if periodo.estado != "borrador":
        raise HTTPException(status_code=409, detail="La nómina ya fue pagada")
    linea = next((ln for ln in periodo.lineas if ln.usuario_id == usuario_id), None)
    if linea is None:
        raise HTTPException(status_code=404, detail="Empleado no está en este periodo")
    if linea.gasto_id is not None:
        raise HTTPException(status_code=409, detail="A este empleado ya se le pagó")
    pago = db.query(EmpleadoPago).filter(EmpleadoPago.usuario_id == usuario_id).first()
    if pago is None:
        raise HTTPException(status_code=409, detail="El empleado ya no tiene tarifas de pago")
    campos = data.model_fields_set
    if "horas_trabajadas" in campos and data.horas_trabajadas is not None:
        linea.horas_trabajadas = data.horas_trabajadas
        linea.horas_ajustadas = True
    if "horas_extra" in campos and data.horas_extra is not None:
        linea.horas_extra = data.horas_extra
        linea.horas_ajustadas = True
    if Decimal(linea.horas_extra) > Decimal(linea.horas_trabajadas):
        raise HTTPException(
            status_code=400, detail="Las horas extra no pueden superar las horas trabajadas"
        )
    if "bonos" in campos and data.bonos is not None:
        linea.bonos = data.bonos
    if "descuentos" in campos and data.descuentos is not None:
        linea.descuentos = data.descuentos
    if "metodo_pago" in campos and data.metodo_pago is not None:
        linea.metodo_pago = data.metodo_pago
    if "sale_de_caja" in campos and data.sale_de_caja is not None:
        linea.sale_de_caja = data.sale_de_caja
    if "notas" in campos:
        linea.notas = (data.notas or "").strip() or None
    # Solo el efectivo puede salir de caja.
    if linea.metodo_pago != "efectivo":
        linea.sale_de_caja = False
    _aplicar_montos(linea, _reglas(pago))
    db.commit()
    db.refresh(periodo)
    return _respuesta(db, periodo)


@router.post("/periodos/{periodo_id}/pagar", response_model=PeriodoNominaResponse)
async def pagar_periodo(
    periodo_id: int,
    data: PagarNominaRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("administrador")),
):
    """Registra como gasto de nómina el pago de los empleados elegidos (uno por método/origen).

    Cada empleado se paga a partir de su último día de trabajo de la semana. Idempotente:
    quien ya está pagado se omite.
    """
    periodo = _periodo(db, periodo_id, current_user.sucursal_id, bloquear=True)
    if periodo.estado == "pagada":
        return _respuesta(db, periodo)
    admin = await verificar_pin_admin(db, data.pin_autorizacion, request, current_user)
    respuesta = _respuesta(db, periodo)
    bloqueos = {ln.usuario_id: ln.bloqueo for ln in respuesta.lineas}
    elegidas = [
        ln
        for ln in periodo.lineas
        if ln.gasto_id is None and (not data.usuario_ids or ln.usuario_id in data.usuario_ids)
    ]
    if data.usuario_ids and not elegidas:
        return respuesta  # ya estaban pagados
    if data.usuario_ids:
        bloqueado = next(
            (bloqueos[ln.usuario_id] for ln in elegidas if bloqueos[ln.usuario_id]), None
        )
        if bloqueado:
            raise HTTPException(status_code=409, detail=bloqueado)
    a_pagar = [ln for ln in elegidas if Decimal(ln.total) > 0 and bloqueos[ln.usuario_id] is None]
    if not a_pagar:
        hay_bloqueados = any(Decimal(ln.total) > 0 and bloqueos[ln.usuario_id] for ln in elegidas)
        raise HTTPException(
            status_code=409 if hay_bloqueados else 400,
            detail="Nadie se puede pagar todavía" if hay_bloqueados else "No hay montos que pagar",
        )
    turno = None
    if any(ln.sale_de_caja for ln in a_pagar):
        turno = obtener_turno_activo(db, periodo.sucursal_id)
        if turno is None:
            raise HTTPException(
                status_code=409, detail="Inicia un turno para pagar nómina desde la caja"
            )
    grupos: dict[tuple[str, bool], list[NominaLinea]] = {}
    for ln in a_pagar:
        grupos.setdefault((ln.metodo_pago, ln.sale_de_caja), []).append(ln)
    descripcion = f"Nómina {periodo.fecha_inicio:%d/%m} al {periodo.fecha_fin:%d/%m}"
    for (metodo, de_caja), lineas in grupos.items():
        total = sum((Decimal(ln.total) for ln in lineas), Decimal(0))
        gasto = Gasto(
            tipo_gasto="nomina",
            metodo_pago=metodo,
            descripcion=descripcion,
            subtotal=total,
            total=total,
            fecha_gasto=get_local_datetime(),
            sucursal_id=periodo.sucursal_id,
            turno_id=turno.id if (de_caja and turno) else None,
            nomina_detalles=[
                NominaDetalle(usuario_id=ln.usuario_id, monto=ln.total, notas=ln.notas)
                for ln in lineas
            ],
        )
        db.add(gasto)
        db.flush()
        for ln in lineas:
            ln.gasto_id = gasto.id
    # La semana se cierra cuando ya no queda nadie con dinero por pagar.
    if all(ln.gasto_id is not None or Decimal(ln.total) <= 0 for ln in periodo.lineas):
        periodo.estado = "pagada"
        periodo.pagado_en = get_local_datetime()
        periodo.pagado_por_id = admin.id
    db.add(
        AutorizacionPin(
            accion="pagar_nomina", ejecutado_por_id=current_user.id, autorizado_por_id=admin.id
        )
    )
    db.commit()
    db.refresh(periodo)
    return _respuesta(db, periodo)
