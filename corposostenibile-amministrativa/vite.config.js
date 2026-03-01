import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001, // Different port from clinica (3000)
    allowedHosts: true,
    proxy: {
      // Proxy API requests to Flask backend (same as clinica)
      '/api': {
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
      // Proxy team routes
      '/team': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
      // Proxy admin routes (for amministrativa specific endpoints)
      '/admin': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
    },
  },
  preview: {
    allowedHosts: true,
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    manifest: true,
    rollupOptions: {
      input: {
        main: './index.html',
      },
    },
  },
})
