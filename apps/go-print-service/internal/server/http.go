// Package server implementa el HTTP server del print service.
package server

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/lahidrocalida/go-print-service/internal/config"
	"github.com/lahidrocalida/go-print-service/internal/dedup"
	"github.com/lahidrocalida/go-print-service/internal/printer"
	"github.com/lahidrocalida/go-print-service/internal/ticket"
)

const version = "2.0.0"

var (
	cfg   *config.Config
	cache *dedup.Cache
)

// Start inicializa y arranca el HTTP server en el puerto configurado.
func Start(c *config.Config) {
	cfg = c
	cache = dedup.New(c.Dedup.TTLSeconds)

	mux := http.NewServeMux()
	mux.HandleFunc("/health", handleHealth)
	mux.HandleFunc("/print", handlePrint)
	mux.HandleFunc("/test", handleTest)
	mux.HandleFunc("/printers", handlePrinters)

	addr := fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port)
	log.Printf("[HTTP] Servicio disponible en http://%s", addr)
	log.Printf("[HTTP] Health: GET http://%s/health", addr)
	log.Printf("[HTTP] Imprimir: POST http://%s/print", addr)

	srv := &http.Server{
		Addr:         addr,
		Handler:      corsMiddleware(mux),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	if err := srv.ListenAndServe(); err != nil {
		log.Fatalf("[HTTP] Error fatal: %v", err)
	}
}

// handleHealth responde el estado del servicio.
func handleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"status":    "ok",
		"service":   "La Hidrocalida Print Service",
		"version":   version,
		"printer":   cfg.Printer.Name,
		"timestamp": time.Now().Format(time.RFC3339),
	})
}

// handlePrint recibe el JSON del ticket y lo imprime de forma asíncrona.
// Retorna 200 inmediatamente para no bloquear el backend en Railway.
func handlePrint(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	var t ticket.TicketData
	if err := logRawJSON(r, &t); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{
			"status":  "error",
			"message": "JSON inválido: " + err.Error(),
		})
		return
	}

	// Retornar 200 inmediatamente
	writeJSON(w, http.StatusOK, map[string]any{
		"status":    "queued",
		"ticket_id": t.NumeroDisplay,
		"message":   "Ticket en cola de impresión",
	})

	// Imprimir en goroutine background
	go printTicket(t)
}

// handleTest imprime un ticket de prueba hardcodeado.
func handleTest(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	now := time.Now()
	testTicket := ticket.TicketData{
		NumeroDisplay: "999",
		Mesa:          "TEST",
		MeseroNombre:  "Sistema",
		FechaLlegada:  now.Add(-30 * time.Minute).Format(time.RFC3339),
		FechaSalida:   now.Format(time.RFC3339),
		Articulos: []ticket.Articulo{
			{Nombre: "Pozole Rojo Grande", Cantidad: 2, Precio: 240.00, Modificaciones: "Extra picante, sin oregano"},
			{Nombre: "Agua de Horchata", Cantidad: 1, Precio: 35.00},
			{Nombre: "Tostadas de Tinga", Cantidad: 3, Precio: 84.00, Modificaciones: "Sin crema"},
		},
		Total: 359.00,
	}

	go printTicket(testTicket)

	writeJSON(w, http.StatusOK, map[string]any{
		"status":  "ok",
		"message": "Ticket de prueba enviado a la impresora",
	})
}

// handlePrinters lista las impresoras disponibles en Windows.
func handlePrinters(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}
	names, err := printer.ListPrinters()
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]any{
			"status":  "error",
			"message": err.Error(),
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"status":   "ok",
		"printers": names,
	})
}

// printTicket formatea e imprime un ticket, con deduplicación y logging.
func printTicket(t ticket.TicketData) {
	// Deduplicación: evitar doble impresión si HTTP y WS llegan juntos
	if !cache.ShouldPrint(t.NumeroDisplay) {
		log.Printf("[DEDUP] Ticket #%s ya impreso recientemente — ignorando duplicado", t.NumeroDisplay)
		return
	}

	log.Printf("[PRINT] Imprimiendo ticket #%s — Mesa: %s — Total: $%.2f", t.NumeroDisplay, t.Mesa, t.Total)

	data := ticket.Format(t)

	if err := printer.PrintRaw(cfg.Printer.Name, data); err != nil {
		log.Printf("[ERROR] Ticket #%s — Error de impresión: %v", t.NumeroDisplay, err)
		return
	}

	log.Printf("[OK] Ticket #%s impreso exitosamente (%d bytes)", t.NumeroDisplay, len(data))
}

// writeJSON escribe una respuesta JSON con el status code dado.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

// corsMiddleware agrega headers CORS para peticiones desde la red local.
func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func logRawJSON(r *http.Request, t *ticket.TicketData) error {

	body, err := io.ReadAll(r.Body)
	if err != nil {
		return err
	}
	log.Printf("[DEBUG] JSON Recibido: %s", string(body))
	return json.Unmarshal(body, t)
}
