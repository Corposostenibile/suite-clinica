import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // Proxy API requests to Flask backend
      '/api': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
      // Proxy customers routes (for CSRF-exempt endpoints)
      '/customers': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
      // Proxy static assets
      '/static': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
      // Proxy uploaded files (avatars, etc.)
      '/uploads': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
      // Proxy team routes (for avatars, etc.)
      '/team': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
      // Proxy client-checks routes
      '/client-checks': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
      // Proxy calendar routes
      '/calendar': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
      // Proxy OAuth routes (Google Calendar connection)
      '/oauth': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
      // Proxy Google OAuth routes (alternative path)
      '/google': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
      // Proxy GHL integration routes
      '/ghl': {
        target: 'http://127.0.0.1:5001',
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
