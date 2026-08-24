"""
Formateador de tickets para impresora térmica ESC/POS
"""
from datetime import datetime

class TicketFormatter:
    def __init__(self):
        """Inicializa el formateador de tickets"""
        self.max_chars = 48  # Caracteres por línea en tamaño normal

    def format_ticket(self, ticket_data):
        """
        Formatea un ticket para impresión térmica

        Args:
            ticket_data (dict): Datos del ticket

        Returns:
            str: Ticket formateado
        """
        lines = []

        # Espacio inicial
        lines.append("")

        # Encabezado del restaurante
        lines.append("*" + "-" * (self.max_chars - 2) + "*")
        lines.append("")
        lines.append("         LA HIDROCALIDA")
        lines.append("")
        lines.append("    POZOLERIA TRADICIONAL")
        lines.append(" Autenticos sabores mexicanos")
        lines.append("")
        lines.append("*" + "-" * (self.max_chars - 2) + "*")
        lines.append("")

        # Información del pedido
        order_num = str(ticket_data.get('numero_display', 'N/A')).zfill(3)
        lines.append(f"ORDEN #{order_num}")

        # Fecha y hora
        from datetime import datetime
        fecha = datetime.now().strftime('%d/%m/%Y')
        hora = datetime.now().strftime('%H:%M')
        lines.append(f"FECHA: {fecha}  HORA: {hora}")
        lines.append("")

        # Información de la mesa y cliente
        if ticket_data.get('mesa'):
            lines.append(f"MESA: {ticket_data['mesa']}")

        if ticket_data.get('nombre_cliente'):
            lines.append(f"CLIENTE: {ticket_data['nombre_cliente']}")

        if ticket_data.get('mesero_nombre'):
            lines.append(f"MESERO: {ticket_data['mesero_nombre']}")

        # Línea separadora
        lines.append("-" * self.max_chars)
        lines.append("")

        # Título de detalles
        title = "~ DETALLES DEL PEDIDO ~"
        padding = (self.max_chars - len(title)) // 2
        lines.append(" " * padding + title)
        lines.append("-" * self.max_chars)
        lines.append("")

        # Artículos
        articulos = ticket_data.get('articulos', [])
        for i, articulo in enumerate(articulos, 1):
            # Nombre del artículo
            nombre = articulo.get('nombre', 'Producto')
            lines.append(f"{i}. {nombre}")

            # Cantidad y precio
            cantidad = articulo.get('cantidad', 1)
            precio_unitario = float(articulo.get('precio', 0))
            precio_total = cantidad * precio_unitario

            # Formato de línea de precio
            precio_line = f"   {cantidad} x ${precio_unitario:.2f}"
            total_str = f"${precio_total:.2f}"
            spaces = self.max_chars - len(precio_line) - len(total_str)
            lines.append(precio_line + " " * spaces + total_str)

            # Modificaciones si existen
            if articulo.get('modificaciones'):
                mod = articulo['modificaciones']
                # Dividir en líneas si es muy largo
                while len(mod) > self.max_chars - 4:
                    cut_pos = mod.rfind(' ', 0, self.max_chars - 4)
                    if cut_pos == -1:
                        cut_pos = self.max_chars - 4
                    lines.append(f"   > {mod[:cut_pos]}")
                    mod = mod[cut_pos:].strip()
                if mod:
                    lines.append(f"   > {mod}")

            lines.append("")

        # Total
        lines.append("-" * self.max_chars)
        lines.append("")

        total = float(ticket_data.get('total', 0))
        total_line = f"TOTAL: ${total:.2f}"
        padding = (self.max_chars - len(total_line)) // 2
        lines.append(" " * padding + total_line)
        lines.append("")

        # Línea separadora doble
        lines.append("=" * self.max_chars)
        lines.append("=" * self.max_chars)
        lines.append("")

        # Mensaje de agradecimiento
        lines.append("MUCHAS GRACIAS!")
        lines.append("Por elegirnos para disfrutar")
        lines.append("de nuestros autenticos pozoles")
        lines.append("")

        # Información del restaurante
        lines.append("* Especialidades de la casa:")
        lines.append("  - Pozole Rojo Tradicional")
        lines.append("  - Pozole Blanco Casero")
        lines.append("  - Tostadas y Garnachas")
        lines.append("")

        # Redes sociales
        lines.append("* Siguenos en redes sociales *")
        lines.append("@lahidrocalida_oficial")
        lines.append("")
        lines.append("Te gusto nuestro servicio?")
        lines.append("Dejanos tu resena *****")
        lines.append("")

        # Pie de página
        from datetime import datetime
        lines.append(f"Sistema POS v1.0 - La Hidrocalida")
        lines.append(f"Impreso: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append("")
        lines.append("")

        return "\n".join(lines)