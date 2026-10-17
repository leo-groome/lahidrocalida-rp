"""DELETE /gastos/articulos/{id}: solo admin y solo si no tiene compras."""

from app.models import Articulo, CategoriaArticulo, Gasto, GastoDetalle


def _articulo(db_session, nombre="Insumo"):
    categoria = CategoriaArticulo(nombre=f"Cat {nombre}")
    db_session.add(categoria)
    db_session.flush()
    articulo = Articulo(nombre=nombre, unidad="kg", costo_estandar=0, categoria_id=categoria.id)
    db_session.add(articulo)
    db_session.commit()
    return articulo


def test_admin_elimina_articulo_sin_compras(como_rol, db_session):
    articulo = _articulo(db_session)
    client = como_rol("administrador")
    assert client.delete(f"/gastos/articulos/{articulo.id}").status_code == 204
    assert db_session.query(Articulo).filter(Articulo.id == articulo.id).count() == 0


def test_articulo_inexistente_404(como_rol):
    assert como_rol("administrador").delete("/gastos/articulos/99999").status_code == 404


def test_articulo_con_compras_409(como_rol, seed, db_session):
    articulo = _articulo(db_session)
    gasto = Gasto(
        sucursal_id=seed["usuario"].sucursal_id,
        tipo_gasto="directo",
        metodo_pago="efectivo",
        subtotal=10,
        total=10,
    )
    db_session.add(gasto)
    db_session.flush()
    db_session.add(
        GastoDetalle(
            gasto_id=gasto.id,
            articulo_id=articulo.id,
            cantidad=1,
            precio_unitario=10,
            subtotal_linea=10,
        )
    )
    db_session.commit()
    assert como_rol("administrador").delete(f"/gastos/articulos/{articulo.id}").status_code == 409
    assert db_session.query(Articulo).filter(Articulo.id == articulo.id).count() == 1


def test_rol_compras_no_puede_eliminar(como_rol, db_session):
    articulo = _articulo(db_session)
    assert como_rol("compras").delete(f"/gastos/articulos/{articulo.id}").status_code == 403
