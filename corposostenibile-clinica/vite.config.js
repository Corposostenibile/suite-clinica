import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { execSync } from 'child_process'
import { readFileSync } from 'fs'

// Build-time app version info: SemVer (da package.json) + git short hash.
// Esposti come 3 var distinte:
//   VITE_APP_SEMVER  → es. "v2.0.0"      (custom field "Versione app")
//   VITE_GIT_COMMIT  → es. "ab12f1"      (custom field "Commit SHA")
//   VITE_APP_VERSION → es. "v2.0.0-ab12f1" (per display UI/tag)
// Override CI/CD: VITE_APP_VERSION_OVERRIDE forza la stringa completa.
function buildVersionInfo(envOverride) {
  let semver = '0.0.0'
  try {
    const pkg = JSON.parse(readFileSync('./package.json', 'utf8'))
    semver = pkg.version || '0.0.0'
  } catch { /* fallback */ }
  let hash = 'local'
  try {
    hash = execSync('git rev-parse --short=7 HEAD', {
      stdio: ['ignore', 'pipe', 'ignore'],
    }).toString().trim() || 'local'
  } catch { /* no git available (e.g. container without .git) */ }
  const fullVersion = envOverride || `v${semver}-${hash}`
  return {
    semver: `v${semver}`,
    commit: hash,
    fullVersion,
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = env.VITE_BACKEND_URL || 'http://127.0.0.1:5001'
  const isDevMode = mode === 'development'
  const versionInfo = buildVersionInfo(env.VITE_APP_VERSION_OVERRIDE)

  return {
    define: {
      // Iniezione build-time
      'import.meta.env.VITE_APP_VERSION': JSON.stringify(versionInfo.fullVersion),
      'import.meta.env.VITE_APP_SEMVER': JSON.stringify(versionInfo.semver),
      'import.meta.env.VITE_GIT_COMMIT': JSON.stringify(versionInfo.commit),
    },
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
