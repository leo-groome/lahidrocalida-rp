package ticket

import (
	"strings"
	"testing"
)

func TestFormat_PrecioUnitarioCorrecto(t *testing.T) {
	// Bug conocido: precio_cobrado = total de línea (NO precio unitario)
	// 2 Pozoles a $120 c/u → precio = 240.00 (total de línea)
	data := TicketData{
		NumeroDisplay: "042",
		Mesa:          "12",
		MeseroNombre:  "Carlos",
		FechaLlegada:  "2026-09-02T14:30:00",
		FechaSalida:   "2026-09-02T15:05:00",
		Articulos: []Articulo{
			{Nombre: "Pozole Rojo Grande", Cantidad: 2, Precio: 240.00},
		},
		Total: 240.00,
	}

	result := Format(data)
	text := string(result)

	// Debe mostrar $120.00 c/u (precio unitario correcto)
	if !strings.Contains(text, "$120.00 c/u") {
		t.Errorf("Se esperaba '$120.00 c/u' en el ticket — precio unitario incorrecto\nTicket:\n%s", text)
	}

	// NO debe mostrar $240.00 c/u (precio inflado del bug anterior)
	if strings.Contains(text, "$240.00 c/u") {
		t.Errorf("Ticket muestra precio unitario inflado '$240.00 c/u' — bug no corregido\nTicket:\n%s", text)
	}

	// Total correcto
	if !strings.Contains(text, "$240.00") {
		t.Errorf("El total $240.00 no aparece en el ticket")
	}
}

func TestFormat_Header(t *testing.T) {
	data := TicketData{NumeroDisplay: "001", Total: 100.00}
	result := Format(data)
	text := string(result)

	checks := []string{
		"POZOLERIA LA HIDROCALIDA",
		"El verdadero amor sabe a Pozole", // eslogan correcto
		"System Designed by Valta Operative",
	}
	for _, check := range checks {
		if !strings.Contains(text, check) {
			t.Errorf("Header falta: %q\nTicket:\n%s", check, text)
		}
	}
}

func TestFormat_FechasFrontend(t *testing.T) {
	// Simula el formato que envía el Frontend de Vue (formatDateTime)
	data := TicketData{
		NumeroDisplay: "001",
		FechaLlegada:  "02/09/2026 20:30",
		FechaSalida:   "--:--",
		Total:         100.00,
	}
	result := Format(data)
	text := string(result)

	// Debe mostrar la fecha parseada
	if !strings.Contains(text, "02/09/2026") {
		t.Errorf("Fecha no aparece — parseo de formato Frontend fallido\nTicket:\n%s", text)
	}
	if !strings.Contains(text, "20:30") {
		t.Errorf("Hora de llegada no aparece en el ticket\nTicket:\n%s", text)
	}
}

func TestFormat_FechaConMicrosegundosYTimezone(t *testing.T) {
	// Simula el formato exacto que envía Railway/PostgreSQL
	data := TicketData{
		NumeroDisplay: "001",
		FechaLlegada:  "2026-09-02T20:30:00.123456-06:00", // RFC3339Nano con offset
		FechaSalida:   "2026-09-02T21:05:30.654321-06:00",
		Total:         100.00,
	}
	result := Format(data)
	text := string(result)

	// Debe mostrar la fecha parseada, no un string vacío
	if !strings.Contains(text, "02/09/2026") {
		t.Errorf("Fecha no aparece en el ticket — parseo RFC3339Nano fallido\nTicket:\n%s", text)
	}
	if !strings.Contains(text, "20:30") {
		t.Errorf("Hora de llegada no aparece en el ticket\nTicket:\n%s", text)
	}
	if !strings.Contains(text, "21:05") {
		t.Errorf("Hora de salida no aparece en el ticket\nTicket:\n%s", text)
	}
}

func TestFormat_Footer(t *testing.T) {
	data := TicketData{NumeroDisplay: "001", Total: 100.00}
	result := Format(data)
	text := string(result)

	checks := []string{
		"Muchas gracias por elegirnos",
		"la_hidrocalida_pozoleria",
		"Valta Operative",
	}
	for _, check := range checks {
		if !strings.Contains(text, check) {
			t.Errorf("Footer falta: %q\nTicket:\n%s", check, text)
		}
	}
}

func TestFormat_SinNumeracionArticulos(t *testing.T) {
	data := TicketData{
		NumeroDisplay: "001",
		Articulos: []Articulo{
			{Nombre: "Pozole Rojo", Cantidad: 1, Precio: 120.00},
		},
		Total: 120.00,
	}
	result := Format(data)
	text := string(result)

	// No debe tener "1." ni "2." como numeración de artículos
	if strings.Contains(text, "1. Pozole") || strings.Contains(text, "1.Pozole") {
		t.Errorf("El ticket no debe numerar artículos con '1.', '2.', etc.")
	}

	// Sí debe tener el nombre del artículo
	if !strings.Contains(text, "Pozole Rojo") {
		t.Errorf("El nombre del artículo no aparece en el ticket")
	}
}

func TestFormat_TotalDestacado(t *testing.T) {
	data := TicketData{NumeroDisplay: "001", Total: 359.00}
	result := Format(data)
	text := string(result)

	if !strings.Contains(text, "*** TOTAL:") {
		t.Errorf("El total debe estar destacado con '***'\nTicket:\n%s", text)
	}
	if !strings.Contains(text, "$359.00") {
		t.Errorf("El total $359.00 no aparece en el ticket")
	}
}

func TestFormat_MesaYMesero(t *testing.T) {
	data := TicketData{
		NumeroDisplay: "001",
		Mesa:          "12",
		MeseroNombre:  "Carlos",
		Total:         100.00,
	}
	result := Format(data)
	text := string(result)

	if !strings.Contains(text, "12") {
		t.Errorf("Número de mesa no aparece en el ticket")
	}
	if !strings.Contains(text, "Carlos") {
		t.Errorf("Nombre del mesero no aparece en el ticket")
	}
}

func TestFormat_Modificaciones(t *testing.T) {
	data := TicketData{
		NumeroDisplay: "001",
		Articulos: []Articulo{
			{Nombre: "Pozole", Cantidad: 1, Precio: 120.00, Modificaciones: "Extra picante"},
		},
		Total: 120.00,
	}
	result := Format(data)
	text := string(result)

	if !strings.Contains(text, "Extra picante") {
		t.Errorf("Modificaciones no aparecen en el ticket")
	}
	if !strings.Contains(text, "> ") {
		t.Errorf("Las modificaciones deben tener prefijo '> '")
	}
}

func TestFormat_ArticuloUnico_UnidadSingular(t *testing.T) {
	data := TicketData{
		NumeroDisplay: "001",
		Articulos: []Articulo{
			{Nombre: "Tostada", Cantidad: 1, Precio: 28.00},
		},
		Total: 28.00,
	}
	result := Format(data)
	text := string(result)

	// 1 unidad → "pza" (singular)
	if !strings.Contains(text, "pza") {
		t.Errorf("1 artículo debe mostrar 'pza' (singular)")
	}
}

func TestFormat_MultiplesArticulos_UnidadPlural(t *testing.T) {
	data := TicketData{
		NumeroDisplay: "001",
		Articulos: []Articulo{
			{Nombre: "Tostada", Cantidad: 3, Precio: 84.00},
		},
		Total: 84.00,
	}
	result := Format(data)
	text := string(result)

	// 3 unidades → "pzs" (plural)
	if !strings.Contains(text, "pzs") {
		t.Errorf("Múltiples artículos deben mostrar 'pzs' (plural)")
	}
}
