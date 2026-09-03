package main

import (
	"fmt"
	"time"
	"github.com/lahidrocalida/go-print-service/internal/ticket"
)

func main() {
	now := time.Now()
	t := ticket.TicketData{
		NumeroDisplay: "042",
		Mesa:          "12",
		MeseroNombre:  "Carlos",
		FechaLlegada:  now.Add(-35 * time.Minute).Format(time.RFC3339),
		FechaSalida:   now.Format(time.RFC3339),
		Articulos: []ticket.Articulo{
			{Nombre: "Pozole Rojo Grande", Cantidad: 2, Precio: 240.00, Modificaciones: "Extra picante, sin oregano"},
			{Nombre: "Agua de Horchata", Cantidad: 1, Precio: 35.00},
			{Nombre: "Tostadas de Tinga", Cantidad: 3, Precio: 84.00, Modificaciones: "Sin crema"},
		},
		Total: 359.00,
	}

	result := ticket.Format(t)
	var clean []byte
	for _, b := range result {
		if (b >= 32 && b <= 126) || b == 10 || b == 13 {
			clean = append(clean, b)
		}
	}
	fmt.Printf("\n===== PREVIEW TICKET (48 chars) =====\n%s\n=====================================\n", string(clean))
}
