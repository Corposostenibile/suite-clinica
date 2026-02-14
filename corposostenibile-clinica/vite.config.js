import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = env.VITE_BACKEND_URL || 'http://127.0.0.1:5001'
  const isProductionBuild = mode === 'production'

  return {
    // In production we publish assets under /static/clinica to avoid clashes
    // with other services that may also expose /assets on the same host.
    base: isProductionBuild ? '/static/clinica/' : '/',
    plugins: [react()],
    server: {
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
      },
    },
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
  }
})
