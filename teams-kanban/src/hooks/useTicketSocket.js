import { useEffect, useRef } from 'react'
import { io } from 'socket.io-client'

/**
 * Connects to WebSocket namespace /team-tickets with bearer token.
 * Calls onEvent(eventName, data) for ticket_created/updated/status_changed.
 */
export function useTicketSocket(token, onEvent) {
  const socketRef = useRef(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    if (!token) return

    const socket = io('/team-tickets', {
      auth: { token },
      transports: ['websocket', 'polling'],
    })

    socket.on('connect', () => {
      console.log('[ws] connected to /team-tickets')
    })

    socket.on('disconnect', (reason) => {
      console.log('[ws] disconnected:', reason)
    })

    const events = ['ticket_created', 'ticket_updated', 'ticket_status_changed']
    events.forEach(evt => {
      socket.on(evt, (data) => {
        onEventRef.current(evt, data)
      })
    })

    socketRef.current = socket

    return () => {
      socket.disconnect()
      socketRef.current = null
    }
  }, [token])
}
