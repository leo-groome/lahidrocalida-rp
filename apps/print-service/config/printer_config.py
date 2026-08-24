"""
Configuración específica para la impresora Easytime SP-POS891ED
"""

# Perfil específico para la impresora Easytime SP-POS891ED
PRINTER_PROFILE = {
    "vendor": "Easytime",
    "model": "SP-POS891ED",
    "width": 80,  # mm
    "dpi": 203,
    "cut": True,
    "buzzer": False,
    "colors": ["black"],
    "text_encodings": ["utf-8", "cp1252", "iso-8859-1"],
    "default_encoding": "cp437",  # Codificación estándar para impresoras térmicas
    "features": {
        "barcode": True,
        "qrcode": True,
        "graphics": False,  # No gráficos en esta impresora
        "pdf417": False
    }
}

# Configuración de conexión para Windows
WINDOWS_PRINTER_CONFIG = {
    "type": "win32raw",
    "printer_name": "Generic / Text Only",  # Nombre por defecto, se puede personalizar
    "port": "LPT1",  # Puerto por defecto
    "baudrate": 9600,
    "bytesize": 8,
    "parity": "N",
    "stopbits": 1
}

# Características del papel térmico
PAPER_CONFIG = {
    "width_mm": 80,
    "printable_width_mm": 72,
    "max_chars_per_line": 48,  # 48 caracteres por línea en tamaño normal
    "max_chars_per_line_wide": 24  # 24 caracteres por línea en tamaño doble
}

# Formato de ticket
TICKET_FORMAT = {
    "header": {
        "double_size": True,
        "center": True,
        "bold": True
    },
    "body": {
        "double_size": False,
        "center": False,
        "bold": False
    },
    "footer": {
        "double_size": False,
        "center": True,
        "bold": False
    }
}