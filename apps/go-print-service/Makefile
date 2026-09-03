.PHONY: build build-windows test vet fmt clean

# Compilar para Windows (desde Linux o Mac)
build-windows:
	GOOS=windows GOARCH=amd64 CGO_ENABLED=0 \
	go build -ldflags="-s -w" -o go-print-service.exe ./cmd/
	@echo "✅ Build exitoso: go-print-service.exe"
	@ls -lh go-print-service.exe

# Compilar para el OS actual (para tests locales)
build:
	go build -o go-print-service-dev ./cmd/
	@echo "✅ Build dev exitoso"

# Tests
test:
	go test ./... -v

# Vet (lint básico)
vet:
	go vet ./...

# Formatear código
fmt:
	gofmt -w .

# Limpiar binarios
clean:
	rm -f go-print-service.exe go-print-service-dev

# Verificar que compila para Windows sin errores
check-windows:
	GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go vet ./...
