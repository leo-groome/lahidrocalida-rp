// Package dedup implementa un cache en memoria para evitar imprimir el mismo ticket dos veces.
package dedup

import (
	"sync"
	"time"
)

// Cache registra los IDs de tickets impresos recientemente para evitar duplicados.
// Es thread-safe y limpia entradas expiradas automáticamente.
type Cache struct {
	mu  sync.Mutex
	seen map[string]time.Time
	ttl  time.Duration
}

// New crea un nuevo Cache con el TTL especificado.
func New(ttlSeconds int) *Cache {
	c := &Cache{
		seen: make(map[string]time.Time),
		ttl:  time.Duration(ttlSeconds) * time.Second,
	}
	go c.cleanup()
	return c
}

// ShouldPrint retorna true si el ticket debe imprimirse (primera vez o TTL expirado).
// Registra el ID al retornar true para bloquear duplicados dentro del TTL.
func (c *Cache) ShouldPrint(id string) bool {
	c.mu.Lock()
	defer c.mu.Unlock()

	if id == "" {
		return true // Sin ID no podemos deduplicar
	}

	if last, ok := c.seen[id]; ok {
		if time.Since(last) < c.ttl {
			return false // Ya impreso recientemente
		}
	}

	c.seen[id] = time.Now()
	return true
}

// cleanup elimina entradas expiradas cada TTL para evitar memory leak
func (c *Cache) cleanup() {
	ticker := time.NewTicker(c.ttl)
	defer ticker.Stop()
	for range ticker.C {
		c.mu.Lock()
		now := time.Now()
		for id, t := range c.seen {
			if now.Sub(t) >= c.ttl {
				delete(c.seen, id)
			}
		}
		c.mu.Unlock()
	}
}
