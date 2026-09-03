// Command go-print-service es el servicio de impresión térmica POS para La Hidrocalida.
// Corre como Windows Service con auto-start y crash-restart automático.
//
// Uso:
//
//	go-print-service.exe            — correr directamente (consola/dev)
//	go-print-service.exe install    — instalar como Windows Service
//	go-print-service.exe start      — iniciar el servicio
//	go-print-service.exe stop       — detener el servicio
//	go-print-service.exe restart    — reiniciar el servicio
//	go-print-service.exe uninstall  — desinstalar el servicio
package main

import (
	"log"
	"os"

	"github.com/kardianos/service"

	"github.com/lahidrocalida/go-print-service/internal/config"
	"github.com/lahidrocalida/go-print-service/internal/server"
)

type program struct {
	cfg *config.Config
}

func (p *program) Start(s service.Service) error {
	go server.Start(p.cfg)
	return nil
}

func (p *program) Stop(s service.Service) error {
	log.Println("[SVC] Servicio detenido")
	return nil
}

func main() {
	// Configurar path del config.yaml relativo al ejecutable
	exePath, _ := os.Executable()
	cfgPath := "config.yaml"
	if exePath != "" {
		// Buscar config.yaml en el mismo directorio que el exe
		dir := exePath[:len(exePath)-len(filepath_base(exePath))]
		if dir != "" {
			cfgPath = dir + "config.yaml"
		}
	}

	cfg := config.Load(cfgPath)

	svcConfig := &service.Config{
		Name:        "LaHidrocalidaPrint",
		DisplayName: "La Hidrocalida Print Service",
		Description: "Servicio de impresion termica POS — Valta Operative",
		// Auto-restart en caso de crash: configurable en services.msc
	}

	prg := &program{cfg: cfg}
	svc, err := service.New(prg, svcConfig)
	if err != nil {
		log.Fatalf("[SVC] Error creando servicio: %v", err)
	}

	// Si se pasa un argumento de control (install/start/stop/restart/uninstall)
	if len(os.Args) > 1 {
		action := os.Args[1]
		log.Printf("[SVC] Ejecutando acción: %s", action)
		if err := service.Control(svc, action); err != nil {
			log.Fatalf("[SVC] Error en '%s': %v", action, err)
		}
		return
	}

	// Sin argumentos: correr como servicio (o en consola en dev)
	log.Println("[SVC] Iniciando La Hidrocalida Print Service v2.0.0")
	log.Printf("[SVC] Impresora configurada: %s", cfg.Printer.Name)
	log.Printf("[SVC] Puerto HTTP: %d", cfg.Server.Port)

	if err := svc.Run(); err != nil {
		log.Fatalf("[SVC] Error fatal: %v", err)
	}
}

// filepath_base extrae el nombre del archivo de una ruta (compatible sin path.filepath)
func filepath_base(path string) string {
	for i := len(path) - 1; i >= 0; i-- {
		if path[i] == '/' || path[i] == '\\' {
			return path[i+1:]
		}
	}
	return path
}
