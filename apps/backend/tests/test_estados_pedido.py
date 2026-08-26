"""domain/estados.py: máquina de estados real de Pedido (S2 2.4)."""

from app.domain.estados import EstadoPedido, transicion_permitida


def test_pendiente_a_preparando_permitido_para_cocina():
    assert transicion_permitida("pendiente", "preparando", "cocina") is True


def test_mesero_no_puede_mandar_a_preparando():
    assert transicion_permitida("pendiente", "preparando", "mesero") is False


def test_estado_terminal_no_admite_ninguna_transicion():
    """El bug que cierra S2: antes solo se validaba el destino, nunca el
    origen — nada impedía "revivir" un pedido ya pagado/cancelado/dividido."""
    for terminal in EstadoPedido.terminales():
        for destino in EstadoPedido:
            for rol in ("mesero", "cajero", "cocina", "administrador"):
                assert transicion_permitida(terminal, destino, rol) is False, (
                    f"{terminal} -> {destino} no debería ser posible para {rol}"
                )


def test_destino_desconocido_es_falso():
    assert transicion_permitida("pendiente", "no-existe", "administrador") is False


def test_origen_desconocido_es_falso():
    assert transicion_permitida("no-existe", "preparando", "cocina") is False


def test_administrador_puede_mover_a_dividido_manualmente():
    """Alcanzable también fuera de /dividir y /dividir_por_montos (menú manual
    de Caja): solo administrador."""
    assert transicion_permitida("cuenta_solicitada", "dividido", "administrador") is True
    assert transicion_permitida("cuenta_solicitada", "dividido", "cajero") is False
