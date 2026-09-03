//go:build !windows

// Stub para compilación en Linux/Mac — no se usa en producción.
package printer

import "fmt"

// PrintRaw en sistemas no-Windows simplemente logea el intento.
func PrintRaw(printerName string, data []byte) error {
	fmt.Printf("[STUB] PrintRaw: '%s' (%d bytes) — solo disponible en Windows\n", printerName, len(data))
	return nil
}

// ListPrinters retorna lista vacía en sistemas no-Windows.
func ListPrinters() ([]string, error) {
	return []string{"[stub - ejecutar en Windows para ver impresoras reales]"}, nil
}
