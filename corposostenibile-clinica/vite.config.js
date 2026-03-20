import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = env.VITE_BACKEND_URL || 'http://127.0.0.1:5001'
  const isDevMode = mode === 'development'

  return {
    // Keep canonical URLs at root (/auth/login, /clienti-lista, ...)
    // while backend APIs stay proxied by Nginx.
    base: '/',
    plugins: [
      react(),
      VitePWA({
        registerType: 'autoUpdate',
        injectRegister: null,
        includeAssets: ['suitemind.png'],
        manifest: {
          name: 'Corposostenibile Suite Clinica',
          short_name: 'Suite Clinica',
          description: 'Corposostenibile Suite - Gestione Clinica',
          theme_color: '#25B36A',
          background_color: '#ffffff',
          display: 'standalone',
          start_url: '.',
          scope: '.',
          icons: [
            {
              src: 'suitemind.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any maskable',
            },
          ],
        },
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg,json,webp,jpg,jpeg}'],
          cleanupOutdatedCaches: true,
          clientsClaim: true,
          skipWaiting: true,
          navigateFallback: 'index.html',
          navigateFallbackDenylist: [
            /^\/api(?:\/|$)/,
            /^\/calendar\/api(?:\/|$)/,
            /^\/loom(?:\/|$)/,
            /^\/ghl\/api(?:\/|$)/,
            /^\/quality\/api(?:\/|$)/,
          ],
          importScripts: ['push-sw.js'],
          maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
        },
      }),
    ],
    server: isDevMode
      ? {
          host: '0.0.0.0',
          port: 3000,
          allowedHosts: true,
          proxy: {
            // Proxy API requests to Flask backend
            '/api': {
              target: backendUrl,
              changeOrigin: true,
            },
            // Proxy customers routes (for CSRF-exempt endpoints)
            '/customers': {
              target: backendUrl,
              changeOrigin: true,
              timeout: 300000,
              proxyTimeout: 300000,
            },
            // Proxy static assets
            '/static': {
              target: backendUrl,
              changeOrigin: true,
            },
            // Proxy uploaded files (avatars, etc.)
            '/uploads': {
              target: backendUrl,
              changeOrigin: true,
            },
            // Note: /team routes are handled by React Router on the frontend
            // Only /api/team/* routes are proxied to the backend
            // Proxy client-checks routes (server-rendered pages, not API)
            '/client-checks': {
              target: backendUrl,
              changeOrigin: true,
            },
            // Proxy calendar routes
            '/calendar': {
              target: backendUrl,
              changeOrigin: true,
            },
            // Proxy OAuth routes (Google Calendar connection)
            '/oauth': {
              target: backendUrl,
              changeOrigin: true,
            },
            // Proxy Google OAuth routes (alternative path)
            '/google': {
              target: backendUrl,
              changeOrigin: true,
            },
            // Proxy GHL integration routes
            '/ghl': {
              target: backendUrl,
              changeOrigin: true,
            },
            // Proxy Quality routes
            '/quality/api': {
              target: backendUrl,
              changeOrigin: true,
            },
            // Proxy Review/Training routes
            '/review': {
              target: backendUrl,
              changeOrigin: true,
            },
            // Proxy Post-it routes
            '/postit': {
              target: backendUrl,
              changeOrigin: true,
            },
            // Proxy Team routes (including trial users API)
            '/team': {
              target: backendUrl,
              changeOrigin: true,
            },
            // Proxy Documentation (MkDocs)
            '/documentation': {
              target: backendUrl,
              changeOrigin: true,
            },
            '/loom': {
              target: backendUrl,
              changeOrigin: true,
            },
            // Proxy Marketing Automation (webhook Frame.io, test-caption, OAuth)
            '/marketing-automation': {
              target: backendUrl,
              changeOrigin: true,
            },
          },
        }
      : undefined,
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      // Generate manifest for Flask integration
      manifest: true,
      rollupOptions: {
        input: {
          main: './index.html',
        },
      },
    },
    preview: {
      allowedHosts: true,
    },
  }
})
