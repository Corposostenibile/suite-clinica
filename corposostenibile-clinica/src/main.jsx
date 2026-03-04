import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { registerSW } from 'virtual:pwa-register'
import ThemeContextProvider from './context/ThemeContext'
import './index.css'
import App from './App.jsx'

const shouldEnablePwa = import.meta.env.VITE_ENABLE_PWA === 'true' || import.meta.env.MODE !== 'development'

if (shouldEnablePwa) {
  const updateSW = registerSW({
    immediate: true,
    onRegisteredSW: (_swUrl, registration) => {
      registration?.update()
      setInterval(() => {
        registration?.update()
      }, 60 * 1000)
    },
    onNeedRefresh: () => {
      updateSW(true)
    },
    onOfflineReady: () => {
      console.info('[PWA] Offline ready')
    },
  })
} else if ('serviceWorker' in navigator) {
  // Avoid stale bundles in local/stage when PWA is disabled.
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    registrations.forEach((registration) => registration.unregister())
  })
  if ('caches' in window) {
    caches.keys().then((keys) => keys.forEach((key) => caches.delete(key)))
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeContextProvider>
      <App />
    </ThemeContextProvider>
  </StrictMode>,
)
