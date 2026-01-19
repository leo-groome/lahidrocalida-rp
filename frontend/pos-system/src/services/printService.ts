/**
 * Servicio de impresión para La Hidrocálida
 * Maneja la conexión con el servidor de impresión local en puerto 3001
 */

import type { PedidoResponse } from '../types'

export interface PrintTicketData {
  numero_display: string
  mesa?: string
  cuenta_label?: string
  nombre_cliente?: string
  mesero_nombre?: string
  fecha_llegada?: string
  fecha_salida?: string
  articulos: Array<{
    cantidad: number
    nombre: string
    precio: number
    modificaciones?: string | null
  }>
  total: number
}

class PrintService {
  private readonly PRINT_SERVICE_URL = 'http://localhost:3001'
  
  /**
   * Verifica si el servicio de impresión está disponible
   */
  async isServiceAvailable(): Promise<boolean> {
    try {
      const response = await fetch(`${this.PRINT_SERVICE_URL}/health`, {
        method: 'GET',
        timeout: 3000
      } as any)
      
      return response.ok
    } catch (error) {
      console.warn('🟡 Servicio de impresión no disponible:', error)
      return false
    }
  }
  
  /**
   * Convierte un pedido a formato de ticket para impresión
   */
  private formatTicketData(pedido: PedidoResponse): PrintTicketData {
    const cuentaMatch = (pedido.nombre_cliente || '').match(/\sCuenta\s(\d+)\/(\d+)\s*$/)
    const cuentaLabel = cuentaMatch ? `Cuenta ${cuentaMatch[1]}/${cuentaMatch[2]}` : undefined

    const hasMesa = Boolean(pedido.mesa)

    // Si hay mesa y el nombre trae "Cuenta i/n":
    // - la cuenta se imprime en la linea de Mesa: "Mesa: 23 Cuenta 2/2"
    // - el cliente se imprime sin el sufijo para no duplicar
    const nombreClienteParaTicket = hasMesa && cuentaLabel
      ? (pedido.nombre_cliente || '').replace(/\sCuenta\s\d+\/\d+\s*$/, '').trim() || undefined
      : (pedido.nombre_cliente || undefined)

    const fechaFmt = (iso?: string | null) => {
      if (!iso) return undefined
      const d = new Date(iso)
      const pad = (n: number) => String(n).padStart(2, '0')
      return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
    }

    return {
      numero_display: pedido.numero_display,
      mesa: pedido.mesa || undefined,
      cuenta_label: hasMesa ? cuentaLabel : undefined,
      nombre_cliente: nombreClienteParaTicket,
      mesero_nombre: (pedido as any).usuario_nombre || undefined,
      fecha_llegada: fechaFmt(pedido.fecha_creacion),
      fecha_salida: fechaFmt((pedido as any).fecha_pago || null),
      articulos: (pedido.articulos_pedido || []).map(articulo => {
        const totalLinea = Number(articulo.precio_cobrado)
        const qty = Math.max(Number(articulo.cantidad || 0), 1)
        const unit = totalLinea / qty

        return {
          cantidad: articulo.cantidad,
          nombre: articulo.platillo?.nombre || 'Producto',
          precio: unit,
          modificaciones: articulo.modificaciones
        }
      }),
      total: Number(pedido.total)
    }
  }
  
  /**
   * Envía ticket a impresora térmica
   */
  async printTicket(pedido: PedidoResponse): Promise<{ success: boolean; method: string; error?: string }> {
    console.log('🖨️ Iniciando proceso de impresión...')
    
    const ticketData = this.formatTicketData(pedido)
    
    // 1. PRIORIDAD 1: Impresora térmica ESC/POS
    try {
      const serviceAvailable = await this.isServiceAvailable()
      
      if (serviceAvailable) {
        console.log('🟢 Servicio de impresión disponible, enviando a impresora térmica...')
        
        const response = await fetch(`${this.PRINT_SERVICE_URL}/print`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(ticketData),
          timeout: 10000
        } as any)
        
        if (response.ok) {
          const result = await response.json()
          console.log('✅ Ticket impreso en impresora térmica:', result)
          return { success: true, method: 'Impresora térmica ESC/POS' }
        } else {
          throw new Error(`Error HTTP ${response.status}: ${response.statusText}`)
        }
      }
    } catch (error) {
      console.warn('❌ Error con impresora térmica:', error)
    }
    
    // 2. PRIORIDAD 2: Impresora del sistema (window.print)
    try {
      console.log('🟡 Fallback: Usando impresora del sistema...')
      
      const success = await this.printWithSystemPrinter(ticketData)
      if (success) {
        return { success: true, method: 'Impresora del sistema' }
      }
    } catch (error) {
      console.warn('❌ Error con impresora del sistema:', error)
    }
    
    // 3. PRIORIDAD 3: Consola del navegador (actual)
    console.log('🔴 Fallback final: Imprimiendo en consola...')
    this.printToConsole(ticketData)
    return { success: true, method: 'Consola del navegador (F12 para ver)' }
  }
  
  /**
   * Imprimir usando window.print() del navegador
   */
  private async printWithSystemPrinter(ticketData: PrintTicketData): Promise<boolean> {
    return new Promise((resolve) => {
      try {
        // Crear ventana temporal para impresión
        const printWindow = window.open('', '_blank', 'width=400,height=600')
        
        if (!printWindow) {
          resolve(false)
          return
        }
        
        // Generar HTML para impresión
        const htmlContent = this.generatePrintHTML(ticketData)
        
        printWindow.document.write(htmlContent)
        printWindow.document.close()
        
        // Esperar a que se cargue y luego imprimir
        printWindow.onload = () => {
          setTimeout(() => {
            printWindow.print()
            
            // Cerrar ventana después de imprimir
            setTimeout(() => {
              printWindow.close()
              resolve(true)
            }, 1000)
          }, 500)
        }
        
        // Timeout de seguridad
        setTimeout(() => {
          printWindow.close()
          resolve(false)
        }, 10000)
        
      } catch (error) {
        console.error('Error en window.print():', error)
        resolve(false)
      }
    })
  }
  
  /**
   * Genera HTML para impresión con window.print()
   */
  private generatePrintHTML(ticketData: PrintTicketData): string {
    const fecha = new Date().toLocaleString('es-MX')
    
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>Ticket - Pedido #${ticketData.numero_display}</title>
        <style>
          @page { 
            size: 80mm auto; 
            margin: 5mm; 
          }
          
          /* Estilos generales - forzar para impresión */
          * {
            box-sizing: border-box;
            -webkit-print-color-adjust: exact !important;
            color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          
          body { 
            font-family: 'Courier New', 'Monaco', 'Lucida Console', monospace !important; 
            font-size: 12px !important; 
            line-height: 1.4 !important;
            margin: 0 !important;
            padding: 10px !important;
            width: 70mm !important;
            color: #000 !important;
            background: #fff !important;
          }
          
          .center { 
            text-align: center !important; 
            display: block !important;
          }
          
          .bold { 
            font-weight: bold !important; 
            font-weight: 700 !important;
          }
          
          .big { 
            font-size: 16px !important; 
            font-weight: bold !important;
          }
          
          .line { 
            border-bottom: 1px dashed #000 !important; 
            margin: 8px 0 !important; 
            width: 100% !important;
            height: 0 !important;
          }
          
          .total { 
            font-size: 14px !important; 
            font-weight: bold !important; 
            font-weight: 700 !important;
          }
          
          .item { 
            margin: 4px 0 !important; 
            display: block !important;
          }
          
          .mod { 
            font-size: 10px !important; 
            color: #333 !important; 
            margin-left: 10px !important; 
          }
          
          /* Reglas específicas para impresión */
          @media print {
            * {
              -webkit-print-color-adjust: exact !important;
              color-adjust: exact !important;
              print-color-adjust: exact !important;
            }
            
            body {
              font-family: 'Courier New', monospace !important;
              color: #000 !important;
              background: #fff !important;
            }
            
            .center {
              text-align: center !important;
            }
            
            .bold {
              font-weight: bold !important;
              font-weight: 700 !important;
            }
            
            .big {
              font-size: 16px !important;
              font-weight: bold !important;
            }
            
            .total {
              font-size: 14px !important;
              font-weight: bold !important;
            }
            
            .line {
              border-bottom: 1px dashed #000 !important;
              border-color: #000 !important;
            }
          }
        </style>
      </head>
      <body>
        <div class="center" style="text-align: center;">
          <div class="bold big" style="font-weight: bold; font-size: 16px; font-weight: 700;"><strong>LA HIDROCÁLIDA</strong></div>
          <div style="text-align: center;">☾ POZOLERÍA TRADICIONAL ☽</div>
          <div style="text-align: center;">Auténticos sabores mexicanos</div>
        </div>
        
        <div class="line" style="border-bottom: 1px dashed #000; margin: 8px 0; width: 100%;"></div>
        
        <div class="bold" style="font-weight: bold; font-weight: 700;"><strong>ORDEN #${ticketData.numero_display}</strong></div>
        <div><strong>Fecha:</strong> ${fecha}</div>
        ${ticketData.mesa ? `<div><strong>Mesa:</strong> ${ticketData.mesa}${ticketData.cuenta_label ? ` ${ticketData.cuenta_label}` : ''}</div>` : ''}
        ${ticketData.nombre_cliente ? `<div><strong>Cliente:</strong> ${ticketData.nombre_cliente}</div>` : ''}
        ${ticketData.mesero_nombre ? `<div><strong>Mesero:</strong> ${ticketData.mesero_nombre}</div>` : ''}
        ${ticketData.fecha_llegada ? `<div><strong>Hora llegada:</strong> ${ticketData.fecha_llegada}</div>` : ''}
        ${ticketData.fecha_salida ? `<div><strong>Hora salida:</strong> ${ticketData.fecha_salida}</div>` : ''}
        
        <div class="line" style="border-bottom: 1px dashed #000; margin: 8px 0; width: 100%;"></div>
        
        <div class="center bold" style="text-align: center; font-weight: bold; font-weight: 700;"><strong>~ DETALLES DEL PEDIDO ~</strong></div>
        
        ${ticketData.articulos.map((articulo, i) => `
          <div class="item" style="margin: 4px 0;">
            <div class="bold" style="font-weight: bold; font-weight: 700;"><strong>${i + 1}. ${articulo.nombre}</strong></div>
            <div>${articulo.cantidad} x $${articulo.precio.toFixed(2)} = <strong>$${(articulo.cantidad * articulo.precio).toFixed(2)}</strong></div>
            ${articulo.modificaciones ? `<div class="mod" style="font-size: 10px; color: #333; margin-left: 10px;">> ${articulo.modificaciones}</div>` : ''}
          </div>
        `).join('')}
        
        <div class="line" style="border-bottom: 1px dashed #000; margin: 8px 0; width: 100%;"></div>
        
        <div class="center" style="text-align: center;">
          <div class="total" style="font-size: 14px; font-weight: bold; font-weight: 700;"><strong>TOTAL: $${ticketData.total.toFixed(2)}</strong></div>
        </div>
        
        <div class="line" style="border-bottom: 1px dashed #000; margin: 8px 0; width: 100%;"></div>
        
        <div class="center" style="text-align: center;">
          <div><strong>¡MUCHAS GRACIAS!</strong></div>
          <div>Por elegirnos para disfrutar</div>
          <div>de nuestros auténticos pozoles</div>
        </div>
        
        <div class="center" style="text-align: center; margin-top: 10px; font-size: 10px;">
          <div>@lahidrocalida_oficial</div>
          <div>Sistema POS v1.0</div>
        </div>
      </body>
      </html>
    `
  }
  
  /**
   * Impresión en consola (fallback final)
   */
  private printToConsole(ticketData: PrintTicketData): void {
    console.log('='.repeat(50))
    console.log('         POZOLERÍA LA HIDROCÁLIDA')
    console.log('     ☾ AUTÉNTICOS SABORES MEXICANOS ☽')
    console.log('='.repeat(50))
    console.log(`Pedido: #${ticketData.numero_display}`)
    console.log(`Fecha: ${new Date().toLocaleString('es-MX')}`)
    if (ticketData.mesa) console.log(`Mesa: ${ticketData.mesa}`)
    if (ticketData.nombre_cliente) console.log(`Cliente: ${ticketData.nombre_cliente}`)
    if (ticketData.mesero_nombre) console.log(`Mesero: ${ticketData.mesero_nombre}`)
    if (ticketData.fecha_llegada) console.log(`Hora llegada: ${ticketData.fecha_llegada}`)
    if (ticketData.fecha_salida) console.log(`Hora salida: ${ticketData.fecha_salida}`)
    console.log('-'.repeat(50))
    
    ticketData.articulos.forEach((articulo, i) => {
      console.log(`${i + 1}. ${articulo.nombre}`)
      console.log(`   ${articulo.cantidad} x $${articulo.precio.toFixed(2)} = $${(articulo.cantidad * articulo.precio).toFixed(2)}`)
      if (articulo.modificaciones) {
        console.log(`   > ${articulo.modificaciones}`)
      }
      console.log('')
    })
    
    console.log('-'.repeat(50))
    console.log(`TOTAL: $${ticketData.total.toFixed(2)}`)
    console.log('='.repeat(50))
    console.log('¡Gracias por su visita!')
    console.log('='.repeat(50))
    console.log('🖨️ Ticket impreso en consola (F12 para ver)')
  }
  
  /**
   * Test de impresión para verificar funcionamiento
   */
  async testPrint(): Promise<{ success: boolean; method: string; error?: string }> {
    console.log('🧪 Ejecutando test de impresión...')
    
    const testTicket: PrintTicketData = {
      numero_display: '999',
      mesa: 'TEST',
      nombre_cliente: 'Prueba del Sistema',
      articulos: [
        {
          cantidad: 1,
          nombre: 'Pozole Rojo Grande',
          precio: 120.00,
          modificaciones: 'Extra picante, sin orégano'
        }
      ],
      total: 120.00
    }
    
    return await this.printTicket({ ...testTicket } as any)
  }
}

export const printService = new PrintService()
export default printService