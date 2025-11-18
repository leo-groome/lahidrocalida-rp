import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'
import { visualizer } from 'rollup-plugin-visualizer'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    // Analizar bundle size
    visualizer({
      filename: 'dist/bundle-analysis.html',
      open: false,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    // Optimizaciones de bundle
    rollupOptions: {
      output: {
        // Separar vendor chunks
        manualChunks: (id) => {
          // Node modules en vendor chunk
          if (id.includes('node_modules')) {
            // Vue ecosystem separado
            if (id.includes('vue') || id.includes('pinia')) {
              return 'vue-vendor'
            }
            // HTTP client separado  
            if (id.includes('axios')) {
              return 'http-vendor'
            }
            // Otros vendors
            return 'vendor'
          }
          
          // Componentes grandes en chunks separados
          if (id.includes('views/AdminView')) {
            return 'admin-chunk'
          }
          if (id.includes('views/CajaView')) {
            return 'caja-chunk'  
          }
          if (id.includes('views/MeseroView')) {
            return 'mesero-chunk'
          }
        }
      }
    },
    // Optimizar assets
    assetsInlineLimit: 4096, // Inline assets < 4kb
    // Comprimir mejor
    target: 'esnext',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.logs en producción
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info', 'console.debug']
      }
    }
  },
  // Optimizaciones de CSS
  css: {
    devSourcemap: false
  }
})
