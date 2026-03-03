import { useState, useEffect, useRef } from 'react'
import { kanbanService } from '../services/kanbanService'

/**
 * Teams SSO → exchange AAD token → JWT
 * Falls back to dev login form when outside Teams.
 */
export function useTeamsAuth() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const attempted = useRef(false)

  useEffect(() => {
    if (attempted.current) return
    attempted.current = true

    async function init() {
      try {
        // Try Teams SDK first
        const teamsJs = await import('@microsoft/teams-js')
        await teamsJs.app.initialize()

        // Get AAD token from Teams
        const aadToken = await teamsJs.authentication.getAuthToken()

        // Exchange for internal JWT
        const result = await kanbanService.authenticate(aadToken)
        setToken(result.token)
        setUser({ id: result.user_id, name: result.name })
      } catch (teamsErr) {
        console.warn('Teams SSO failed, trying dev mode:', teamsErr.message)

        // Dev fallback: check sessionStorage for saved token
        const saved = sessionStorage.getItem('kb_auth')
        if (saved) {
          try {
            const parsed = JSON.parse(saved)
            setToken(parsed.token)
            setUser({ id: parsed.user_id, name: parsed.name })
            return
          } catch {
            sessionStorage.removeItem('kb_auth')
          }
        }

        // Show dev login
        setError('DEV_LOGIN')
      } finally {
        setLoading(false)
      }
    }

    init()
  }, [])

  /** Dev login handler */
  const devLogin = async (username, password) => {
    setLoading(true)
    setError(null)
    try {
      const result = await kanbanService.devLogin(username, password)
      setToken(result.token)
      setUser({ id: result.user_id, name: result.name })
      sessionStorage.setItem('kb_auth', JSON.stringify(result))
    } catch (err) {
      setError(err.response?.data?.error || 'Login fallito')
    } finally {
      setLoading(false)
    }
  }

  return { user, token, loading, error, devLogin }
}
