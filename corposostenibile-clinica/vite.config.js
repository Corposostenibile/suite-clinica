import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:5001';

// https://vite.dev/config/
export default defineConfig({
  base: '/',
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
})
