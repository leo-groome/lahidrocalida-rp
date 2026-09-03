//go:build windows

// Package printer implementa impresión raw vía Win32 API para impresoras térmicas USB.
// No requiere CGO — usa golang.org/x/sys/windows para las syscalls.
package printer

import (
	"fmt"
	"unsafe"

	"golang.org/x/sys/windows"
)

var (
	winspool          = windows.NewLazyDLL("winspool.drv")
	procOpenPrinter   = winspool.NewProc("OpenPrinterW")
	procClosePrinter  = winspool.NewProc("ClosePrinter")
	procStartDocPrinter = winspool.NewProc("StartDocPrinterW")
	procEndDocPrinter   = winspool.NewProc("EndDocPrinter")
	procStartPagePrinter = winspool.NewProc("StartPagePrinter")
	procEndPagePrinter   = winspool.NewProc("EndPagePrinter")
	procWritePrinter    = winspool.NewProc("WritePrinter")
	procEnumPrinters    = winspool.NewProc("EnumPrintersW")
)

// docInfo1 corresponde a DOC_INFO_1W en la Win32 API
type docInfo1 struct {
	DocName    *uint16
	OutputFile *uint16
	Datatype   *uint16
}

// PrintRaw envía bytes crudos ESC/POS directamente a la impresora Windows indicada.
// printerName debe coincidir exactamente con el nombre en "Dispositivos e impresoras".
func PrintRaw(printerName string, data []byte) error {
	if len(data) == 0 {
		return fmt.Errorf("datos de impresión vacíos")
	}

	namePtr, err := windows.UTF16PtrFromString(printerName)
	if err != nil {
		return fmt.Errorf("nombre de impresora inválido: %w", err)
	}

	// OpenPrinter
	var hPrinter windows.Handle
	r, _, err := procOpenPrinter.Call(
		uintptr(unsafe.Pointer(namePtr)),
		uintptr(unsafe.Pointer(&hPrinter)),
		0,
	)
	if r == 0 {
		return fmt.Errorf("OpenPrinter falló para '%s': %w", printerName, err)
	}
	defer procClosePrinter.Call(uintptr(hPrinter))

	// StartDocPrinter con tipo RAW
	docName, _ := windows.UTF16PtrFromString("Ticket La Hidrocalida")
	datatype, _ := windows.UTF16PtrFromString("RAW")
	di := docInfo1{
		DocName:  docName,
		Datatype: datatype,
	}
	r, _, err = procStartDocPrinter.Call(
		uintptr(hPrinter),
		1,
		uintptr(unsafe.Pointer(&di)),
	)
	if r == 0 {
		return fmt.Errorf("StartDocPrinter falló: %w", err)
	}
	defer procEndDocPrinter.Call(uintptr(hPrinter))

	// StartPagePrinter
	r, _, err = procStartPagePrinter.Call(uintptr(hPrinter))
	if r == 0 {
		return fmt.Errorf("StartPagePrinter falló: %w", err)
	}
	defer procEndPagePrinter.Call(uintptr(hPrinter))

	// WritePrinter — enviar bytes ESC/POS
	var written uint32
	r, _, err = procWritePrinter.Call(
		uintptr(hPrinter),
		uintptr(unsafe.Pointer(&data[0])),
		uintptr(len(data)),
		uintptr(unsafe.Pointer(&written)),
	)
	if r == 0 {
		return fmt.Errorf("WritePrinter falló: %w", err)
	}
	if int(written) != len(data) {
		return fmt.Errorf("WritePrinter: enviados %d de %d bytes", written, len(data))
	}

	return nil
}

// ListPrinters retorna los nombres de las impresoras instaladas en Windows.
func ListPrinters() ([]string, error) {
	const PRINTER_ENUM_LOCAL = 0x00000002
	const PRINTER_ENUM_CONNECTIONS = 0x00000004

	var needed, returned uint32

	// Primera llamada para obtener el tamaño del buffer
	procEnumPrinters.Call(
		PRINTER_ENUM_LOCAL|PRINTER_ENUM_CONNECTIONS,
		0,
		2, // nivel de info
		0,
		0,
		uintptr(unsafe.Pointer(&needed)),
		uintptr(unsafe.Pointer(&returned)),
	)

	if needed == 0 {
		return nil, nil
	}

	buf := make([]byte, needed)
	r, _, err := procEnumPrinters.Call(
		PRINTER_ENUM_LOCAL|PRINTER_ENUM_CONNECTIONS,
		0,
		2,
		uintptr(unsafe.Pointer(&buf[0])),
		uintptr(needed),
		uintptr(unsafe.Pointer(&needed)),
		uintptr(unsafe.Pointer(&returned)),
	)
	if r == 0 {
		return nil, fmt.Errorf("EnumPrinters falló: %w", err)
	}

	// PRINTER_INFO_2 — offset del nombre es 0 (pName es primer campo)
	const printerInfo2Size = 136 // tamaño de PRINTER_INFO_2W en 64-bit
	var names []string
	for i := uint32(0); i < returned; i++ {
		offset := uintptr(i) * printerInfo2Size
		namePtr := *(**uint16)(unsafe.Pointer(&buf[offset]))
		if namePtr != nil {
			names = append(names, windows.UTF16PtrToString(namePtr))
		}
	}
	return names, nil
}
