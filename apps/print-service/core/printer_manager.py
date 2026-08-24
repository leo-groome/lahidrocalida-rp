"""
Gestor de impresión para la impresora Easytime SP-POS891ED
"""
import logging
from escpos.printer import Win32Raw
from escpos.printer import Dummy  # Para pruebas
from config.printer_config import WINDOWS_PRINTER_CONFIG, PRINTER_PROFILE
from config.settings import PRINTER_NAME

class PrinterManager:
    def __init__(self, printer_name=None):
        """
        Inicializa el gestor de impresión
        
        Args:
            printer_name (str): Nombre de la impresora a usar
        """
        self.logger = logging.getLogger(__name__)
        self.printer_name = printer_name or PRINTER_NAME
        self.printer = None
        self._connect_printer()
    
    def _connect_printer(self):
        """Conecta con la impresora"""
        try:
            # Intentar conectar con la impresora usando Win32Raw
            self.printer = Win32Raw(printer_name=self.printer_name)
            self.logger.info(f"[OK] Conectado a la impresora: {self.printer_name}")
        except Exception as e:
            self.logger.warning(f"[WARN] No se pudo conectar a la impresora fisica: {e}")
            self.logger.info("[INFO] Usando impresora Dummy para pruebas")
            self.printer = Dummy()
    
    def print_ticket(self, ticket_data):
        """
        Imprime un ticket usando comandos ESC/POS
        
        Args:
            ticket_data (dict): Datos del ticket a imprimir
        """
        try:
            # Abrir conexión con la impresora
            if hasattr(self.printer, 'open'):
                self.printer.open()
            
            # Inicializar impresora
            if hasattr(self.printer, 'init'):
                self.printer.init()
            
            # Imprimir el ticket
            self._format_and_print_ticket(ticket_data)
            
            # Cortar papel
            if hasattr(self.printer, 'cut'):
                self.printer.cut()
            
            # Cerrar conexión
            if hasattr(self.printer, 'close'):
                self.printer.close()
            
            self.logger.info("[OK] Ticket impreso exitosamente")
            return True

        except Exception as e:
            self.logger.error(f"[ERROR] Error al imprimir ticket: {e}")
            return False
    
    def _format_and_print_ticket(self, ticket_data):
        """Formatea e imprime el ticket"""
        try:
            from core.ticket_formatter import TicketFormatter

            # Crear formateador de tickets
            formatter = TicketFormatter()

            # Formatear ticket
            formatted_ticket = formatter.format_ticket(ticket_data)

            # Imprimir ticket formateado
            self.printer.text(formatted_ticket)
        except ImportError as e:
            self.logger.error(f"Error importando TicketFormatter: {e}")
            # Fallback: imprimir datos básicos
            basic_text = f"Ticket #{ticket_data.get('numero_display', 'N/A')}\nTotal: ${ticket_data.get('total', 0):.2f}\n"
            self.printer.text(basic_text)
    
    def test_printer(self):
        """Prueba la conexión con la impresora"""
        try:
            if hasattr(self.printer, 'open'):
                self.printer.open()
            self.printer.text("Test de impresora - La Hidrocálida\n")
            if hasattr(self.printer, 'cut'):
                self.printer.cut()
            if hasattr(self.printer, 'close'):
                self.printer.close()
            self.logger.info("[OK] Test de impresora exitoso")
            return True
        except Exception as e:
            self.logger.error(f"[ERROR] Test de impresora fallido: {e}")
            return False
    
    def get_available_printers(self):
        """Obtiene la lista de impresoras disponibles"""
        try:
            return self.printer.printers
        except:
            return {}

# Instancia global del gestor de impresión
printer_manager = PrinterManager()