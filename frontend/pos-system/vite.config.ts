import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['apple-touch-icon.png', 'icons/*.png'],
      manifest: {
        name: 'La Hidrocálida POS',
        short_name: 'Hidrocálida',
        description: 'Sistema POS - La Hidrocálida',
        start_url: '/login',
        display: 'standalone',
        background_color: '#0f172a',
        theme_color: '#e11d48',
        orientation: 'any',
        icons: [
          { src: '/icons/icon-72x72.png', sizes: '72x72', type: 'image/png' },
          { src: '/icons/icon-96x96.png', sizes: '96x96', type: 'image/png' },
          { src: '/icons/icon-128x128.png', sizes: '128x128', type: 'image/png' },
          { src: '/icons/icon-144x144.png', sizes: '144x144', type: 'image/png' },
          { src: '/icons/icon-152x152.png', sizes: '152x152', type: 'image/png' },
          { src: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-384x384.png', sizes: '384x384', type: 'image/png' },
          { src: '/icons/icon-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icons/icon-maskable-192x192.png', sizes: '192x192', type: 'image/png', purpose: 'maskable' },
          { src: '/icons/icon-maskable-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.port === '8000',
            handler: 'NetworkFirst',
            options: {
              cacheName: 'backend-cache',
              expiration: { maxEntries: 100, maxAgeSeconds: 300 },
              networkTimeoutSeconds: 10,
            },
          },
        ],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/ws\//],
      },
      devOptions: {
        enabled: true,
      },
    }),
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
