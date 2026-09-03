// Package ticket implementa el formateador de tickets para La Hidrocalida.
package ticket

import (
	"bytes"
	"fmt"
	"strings"
	"time"

	"github.com/lahidrocalida/go-print-service/internal/escpos"
)

const maxChars = 48

// TicketData representa los datos del ticket recibidos desde el backend.
// El campo Precio en Articulo es precio_cobrado (total de línea, NO precio unitario).
type TicketData struct {
	NumeroDisplay string     `json:"numero_display"`
	Mesa          string     `json:"mesa"`
	NombreCliente string     `json:"nombre_cliente"`
	MeseroNombre  string     `json:"mesero_nombre"`
	FechaLlegada  string     `json:"fecha_llegada"` // ISO8601 fecha_creacion
	FechaSalida   string     `json:"fecha_salida"`  // ISO8601 momento cuenta_solicitada
	Articulos     []Articulo `json:"articulos"`
	Total         float64    `json:"total"`
}

// Articulo representa un artículo del pedido.
type Articulo struct {
	Nombre         string  `json:"nombre"`
	Cantidad       int     `json:"cantidad"`
	Precio         float64 `json:"precio"`         // precio_cobrado = TOTAL de línea
	Modificaciones string  `json:"modificaciones"`
}

// Format genera los bytes ESC/POS completos del ticket, listos para WritePrinter.
func Format(t TicketData) []byte {
	var buf bytes.Buffer

	write := func(b []byte) { buf.Write(b) }
	writeln := func(s string) { buf.Write(escpos.Text(s + "\n")) }
	center := func(s string) string { return centerStr(s, maxChars) }
	separator := func(ch string) string { return strings.Repeat(ch, maxChars) }

	// ── Inicializar impresora ──────────────────────────────────────────────
	write(escpos.Init)
	write(escpos.AlignCenter)

	// ── Header ────────────────────────────────────────────────────────────
	writeln(separator("="))
	writeln(center("POZOLERIA LA HIDROCALIDA"))
	writeln(center("El verdadero amor sabe a Pozole"))
	writeln(center("System Designed by Valta Operative"))
	writeln(separator("="))
	writeln("")

	// ── Info del pedido ───────────────────────────────────────────────────
	write(escpos.AlignLeft)

	orderNum := padLeft(t.NumeroDisplay, 3, '0')
	writeln(fmt.Sprintf("ORDEN #%s", orderNum))

	// Parsear fechas
	llegada := parseFecha(t.FechaLlegada)
	salida := parseFechaHora(t.FechaSalida)
	fecha := ""
	horaLlegada := ""
	horaSalida := ""

	if llegada != (time.Time{}) {
		fecha = llegada.Format("02/01/2006")
		horaLlegada = llegada.Format("15:04")
	}
	if salida != (time.Time{}) {
		horaSalida = salida.Format("15:04")
	}

	writeln(fmt.Sprintf("Fecha:   %s", fecha))

	// Llegada y Salida en la misma línea si ambos existen
	if horaLlegada != "" && horaSalida != "" {
		col1 := fmt.Sprintf("Llegada: %s", horaLlegada)
		col2 := fmt.Sprintf("Salida: %s", horaSalida)
		writeln(colsLine(col1, col2, maxChars))
	} else if horaLlegada != "" {
		writeln(fmt.Sprintf("Llegada: %s", horaLlegada))
	}

	// Mesa y Mesero
	if t.Mesa != "" || t.MeseroNombre != "" {
		col1 := ""
		col2 := ""
		if t.Mesa != "" {
			col1 = fmt.Sprintf("Mesa:    %s", t.Mesa)
		}
		if t.MeseroNombre != "" {
			col2 = fmt.Sprintf("Mesero: %s", t.MeseroNombre)
		}
		if col1 != "" && col2 != "" {
			writeln(colsLine(col1, col2, maxChars))
		} else if col1 != "" {
			writeln(col1)
		} else {
			writeln(col2)
		}
	}

	writeln("")
	writeln(separator("-"))

	// Centrar título de detalles
	write(escpos.AlignCenter)
	writeln(center("DETALLES DEL PEDIDO"))
	write(escpos.AlignLeft)
	writeln(separator("-"))

	// ── Artículos ─────────────────────────────────────────────────────────
	for i, a := range t.Articulos {
		if i > 0 {
			writeln("") // separador solo ENTRE artículos, no antes del primero
		}

		// Nombre del artículo
		writeln(truncate(a.Nombre, maxChars))

		// Calcular precio unitario correctamente
		// precio_cobrado del backend = total de línea (ya incluye cantidad)
		cantidad := a.Cantidad
		if cantidad < 1 {
			cantidad = 1
		}
		precioUnitario := a.Precio / float64(cantidad)
		totalLinea := a.Precio

		// Unidad: pza / pzs
		unidad := "pza"
		if cantidad > 1 {
			unidad = "pzs"
		}

		// Línea: "  2 pzs  $120.00 c/u            $240.00"
		leftPart := fmt.Sprintf("  %d %s  $%.2f c/u", cantidad, unidad, precioUnitario)
		rightPart := fmt.Sprintf("$%.2f", totalLinea)
		spaces := maxChars - len(leftPart) - len(rightPart)
		if spaces < 1 {
			spaces = 1
		}
		writeln(leftPart + strings.Repeat(" ", spaces) + rightPart)

		// Modificaciones (con word-wrap)
		if a.Modificaciones != "" {
			for _, line := range wrapText("  > "+a.Modificaciones, maxChars) {
				writeln(line)
			}
		}
	}

	writeln("")
	writeln(separator("-"))
	writeln("")

	// ── Total ─────────────────────────────────────────────────────────────
	write(escpos.AlignCenter)
	write(escpos.BoldOn)
	totalStr := fmt.Sprintf("*** TOTAL:  $%.2f ***", t.Total)
	writeln(center(totalStr))
	write(escpos.BoldOff)
	writeln("")
	writeln(separator("="))
	writeln("")

	// ── Footer ────────────────────────────────────────────────────────────
	writeln(center("!Muchas gracias por elegirnos!"))
	writeln("")
	writeln(center("Instagram: @la_hidrocalida_pozoleria"))
	writeln("")
	writeln(center("System Designed by Valta Operative"))
	writeln("")

	// ── Corte de papel ────────────────────────────────────────────────────
	write(escpos.Feed5)
	write(escpos.CutFull)

	return buf.Bytes()
}

// ── Helpers ───────────────────────────────────────────────────────────────────

func centerStr(s string, width int) string {
	if len(s) >= width {
		return s
	}
	pad := (width - len(s)) / 2
	return strings.Repeat(" ", pad) + s
}

// colsLine alinea dos strings: izquierda y derecha, relleno en medio
func colsLine(left, right string, width int) string {
	spaces := width - len(left) - len(right)
	if spaces < 1 {
		spaces = 1
	}
	return left + strings.Repeat(" ", spaces) + right
}

func truncate(s string, max int) string {
	if len(s) <= max {
		return s
	}
	return s[:max-1] + "…"
}

func padLeft(s string, n int, pad rune) string {
	for len(s) < n {
		s = string(pad) + s
	}
	return s
}

// wrapText divide un texto en líneas de longitud máxima `width`, respetando palabras
func wrapText(text string, width int) []string {
	if len(text) <= width {
		return []string{text}
	}
	var lines []string
	for len(text) > width {
		cut := strings.LastIndex(text[:width], " ")
		if cut <= 0 {
			cut = width
		}
		lines = append(lines, text[:cut])
		text = strings.TrimLeft(text[cut:], " ")
	}
	if text != "" {
		lines = append(lines, text)
	}
	return lines
}

// parseFecha intenta parsear un timestamp ISO8601 (con o sin timezone)
func parseFecha(s string) time.Time {
	if s == "" {
		return time.Time{}
	}
	formats := []string{
		time.RFC3339Nano, // Railway
		time.RFC3339,
		"02/01/2006 15:04",    // Frontend UI (es-MX formatDateTime)
		"02/01/2006 15:04:05", // Frontend UI alt
		"02/01/2006  15:04",   // Frontend UI alt con doble espacio (por replace ',')
		"2006-01-02T15:04:05",
		"2006-01-02T15:04:05.999999",
		"2006-01-02T15:04:05Z",
		"2006-01-02",
	}
	for _, f := range formats {
		if t, err := time.Parse(f, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

// parseFechaHora es alias de parseFecha (ambas retornan time.Time)
func parseFechaHora(s string) time.Time {
	return parseFecha(s)
}
