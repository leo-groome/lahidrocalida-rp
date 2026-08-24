"""
Sistema de cola de impresión para manejar fallos temporales
"""
import json
import os
import time
import threading
from datetime import datetime
from config.settings import MAX_RETRY_ATTEMPTS, RETRY_INTERVAL_SECONDS
from config.settings import BASE_DIR

class PrintQueue:
    def __init__(self):
        """Inicializa la cola de impresión"""
        self.queue_file = os.path.join(BASE_DIR, "logs", "print_queue.json")
        self.failed_tickets_dir = os.path.join(BASE_DIR, "logs", "failed_tickets")
        self.lock = threading.Lock()
        
        # Crear directorio de tickets fallidos si no existe
        if not os.path.exists(self.failed_tickets_dir):
            os.makedirs(self.failed_tickets_dir)
        
        # Inicializar cola si no existe
        if not os.path.exists(self.queue_file):
            self._initialize_queue()
    
    def _initialize_queue(self):
        """Inicializa la cola de impresión"""
        with self.lock:
            queue_data = {
                "pending": [],
                "failed": [],
                "processing": []
            }
            self._save_queue(queue_data)
    
    def _load_queue(self):
        """Carga la cola de impresión desde el archivo"""
        try:
            if os.path.exists(self.queue_file):
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"pending": [], "failed": [], "processing": []}
        except Exception as e:
            print(f"Error cargando cola: {e}")
            return {"pending": [], "failed": [], "processing": []}
    
    def _save_queue(self, queue_data):
        """Guarda la cola de impresión en el archivo"""
        try:
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error guardando cola: {e}")
    
    def add_to_queue(self, ticket_data):
        """
        Agrega un ticket a la cola de impresión
        
        Args:
            ticket_data (dict): Datos del ticket a imprimir
        """
        with self.lock:
            queue_data = self._load_queue()
            
            # Agregar intento de impresión
            ticket_data['retry_count'] = 0
            ticket_data['timestamp'] = datetime.now().isoformat()
            
            queue_data['pending'].append(ticket_data)
            self._save_queue(queue_data)
            
            print(f"[OK] Ticket #{ticket_data.get('numero_display', 'N/A')} agregado a la cola")
    
    def process_queue(self, printer_manager):
        """
        Procesa la cola de impresión
        
        Args:
            printer_manager (PrinterManager): Gestor de impresión
        """
        with self.lock:
            queue_data = self._load_queue()
            
            # Procesar tickets pendientes
            pending_tickets = queue_data['pending'][:]
            for ticket in pending_tickets:
                success = self._process_ticket(ticket, printer_manager)
                if success:
                    # Remover ticket de la cola pendiente
                    queue_data['pending'].remove(ticket)
                else:
                    # Incrementar contador de reintentos
                    ticket['retry_count'] = ticket.get('retry_count', 0) + 1
                    if ticket['retry_count'] >= MAX_RETRY_ATTEMPTS:
                        # Mover a fallidos si se exceden los reintentos
                        queue_data['pending'].remove(ticket)
                        queue_data['failed'].append(ticket)
                        self._save_failed_ticket(ticket)
            
            self._save_queue(queue_data)
    
    def _process_ticket(self, ticket_data, printer_manager):
        """
        Procesa un ticket individual

        Args:
            ticket_data (dict): Datos del ticket
            printer_manager (PrinterManager): Gestor de impresión

        Returns:
            bool: True si se imprimió exitosamente, False si falló
        """
        try:
            # Intentar imprimir el ticket
            success = printer_manager.print_ticket(ticket_data)

            if success:
                print(f"[OK] Ticket #{ticket_data.get('numero_display', 'N/A')} impreso exitosamente")
                return True
            else:
                print(f"[WARN] Ticket #{ticket_data.get('numero_display', 'N/A')} fallo, se reintentara")
                return False

        except Exception as e:
            print(f"[ERROR] Error procesando ticket #{ticket_data.get('numero_display', 'N/A')}: {e}")
            return False
    
    def _save_failed_ticket(self, ticket_data):
        """
        Guarda un ticket fallido en archivo separado
        
        Args:
            ticket_data (dict): Datos del ticket fallido
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ticket_{ticket_data.get('numero_display', 'unknown')}_{timestamp}.json"
            filepath = os.path.join(self.failed_tickets_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(ticket_data, f, ensure_ascii=False, indent=2)
                
            print(f"[SAVE] Ticket fallido guardado: {filename}")
        except Exception as e:
            print(f"Error guardando ticket fallido: {e}")

# Instancia global de la cola de impresión
print_queue = PrintQueue()