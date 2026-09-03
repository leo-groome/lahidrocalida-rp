// Package escpos define los bytes de control ESC/POS para impresoras térmicas genéricas.
package escpos

// Comandos ESC/POS estándar
var (
	// Init inicializa la impresora y borra el buffer
	Init = []byte{0x1B, 0x40}

	// Alineación de texto
	AlignLeft   = []byte{0x1B, 0x61, 0x00}
	AlignCenter = []byte{0x1B, 0x61, 0x01}
	AlignRight  = []byte{0x1B, 0x61, 0x02}

	// Negrita
	BoldOn  = []byte{0x1B, 0x45, 0x01}
	BoldOff = []byte{0x1B, 0x45, 0x00}

	// Avance de papel
	Feed1 = []byte{0x1B, 0x64, 0x01}
	Feed2 = []byte{0x1B, 0x64, 0x02}
	Feed3 = []byte{0x1B, 0x64, 0x03}
	Feed5 = []byte{0x1B, 0x64, 0x05}

	// Corte de papel — full cut con 5 líneas de avance
	CutFull = []byte{0x1D, 0x56, 0x41, 0x05}
)

// Text convierte un string a bytes CP437 — codificación estándar de impresoras térmicas.
// Los caracteres ASCII básicos (32-126) son directamente compatibles.
// Caracteres especiales españoles se transliteran para máxima compatibilidad.
func Text(s string) []byte {
	return []byte(transliterate(s))
}

// transliterate convierte caracteres Unicode a su equivalente ASCII seguro
func transliterate(s string) string {
	replacements := map[rune]string{
		'á': "a", 'é': "e", 'í': "i", 'ó': "o", 'ú': "u",
		'Á': "A", 'É': "E", 'Í': "I", 'Ó': "O", 'Ú': "U",
		'ñ': "n", 'Ñ': "N",
		'ü': "u", 'Ü': "U",
		'¿': "?", '¡': "!",
		'«': "\"", '»': "\"",
	}

	out := make([]rune, 0, len(s))
	for _, r := range s {
		if rep, ok := replacements[r]; ok {
			for _, c := range rep {
				out = append(out, c)
			}
		} else {
			out = append(out, r)
		}
	}
	return string(out)
}
