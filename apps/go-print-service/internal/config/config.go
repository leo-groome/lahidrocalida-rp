package config

import (
	"log"
	"os"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Printer PrinterConfig `yaml:"printer"`
	Server  ServerConfig  `yaml:"server"`
	Dedup   DedupConfig   `yaml:"dedup"`
	Log     LogConfig     `yaml:"log"`
}

type PrinterConfig struct {
	Name      string `yaml:"name"`
	TimeoutMs int    `yaml:"timeout_ms"`
}

type ServerConfig struct {
	Port int    `yaml:"port"`
	Host string `yaml:"host"`
}

type DedupConfig struct {
	TTLSeconds int `yaml:"ttl_seconds"`
}

type LogConfig struct {
	Level string `yaml:"level"`
	File  string `yaml:"file"`
}

func Load(path string) *Config {
	cfg := &Config{
		Printer: PrinterConfig{Name: "Generic / Text Only", TimeoutMs: 5000},
		Server:  ServerConfig{Port: 3001, Host: "localhost"},
		Dedup:   DedupConfig{TTLSeconds: 60},
		Log:     LogConfig{Level: "info", File: "print-service.log"},
	}

	data, err := os.ReadFile(path)
	if err != nil {
		log.Printf("[CONFIG] No se encontró %s — usando valores por defecto", path)
		return cfg
	}

	if err := yaml.Unmarshal(data, cfg); err != nil {
		log.Printf("[CONFIG] Error leyendo %s: %v — usando valores por defecto", path, err)
	}

	return cfg
}
