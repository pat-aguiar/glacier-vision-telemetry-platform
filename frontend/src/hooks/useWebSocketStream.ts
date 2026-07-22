import { useEffect, useRef, useState } from "react"

export type ConnectionStatus = "connecting" | "open" | "closed" | "reconnecting"

export interface UseWebSocketStreamOptions<T> {
  onMessage: (data: T) => void
  /** Set to false to close the socket and stop reconnecting. */
  enabled?: boolean
  baseDelayMs?: number
  maxDelayMs?: number
}

/**
 * Maintains a WebSocket connection to `url`, reconnecting on any close or
 * error with exponential backoff (+ jitter, capped at `maxDelayMs`). The
 * backoff resets to `baseDelayMs` after every successful connection.
 */
export function useWebSocketStream<T>(
  url: string,
  { onMessage, enabled = true, baseDelayMs = 500, maxDelayMs = 30_000 }: UseWebSocketStreamOptions<T>,
): ConnectionStatus {
  const [status, setStatus] = useState<ConnectionStatus>("connecting")

  // Kept in a ref so reconnects/effect re-runs don't depend on identity of
  // the caller's callback -- only `url`/`enabled`/backoff bounds do.
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  useEffect(() => {
    if (!enabled) {
      setStatus("closed")
      return
    }

    let socket: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined
    let attempt = 0
    let stopped = false

    const scheduleReconnect = () => {
      const delay = Math.min(baseDelayMs * 2 ** attempt, maxDelayMs)
      const jitteredDelay = delay * (0.5 + Math.random() * 0.5)
      attempt += 1
      reconnectTimer = setTimeout(connect, jitteredDelay)
    }

    function connect() {
      setStatus(attempt === 0 ? "connecting" : "reconnecting")
      socket = new WebSocket(url)

      socket.onopen = () => {
        attempt = 0
        setStatus("open")
      }

      socket.onmessage = (event) => {
        try {
          onMessageRef.current(JSON.parse(event.data as string) as T)
        } catch {
          // Malformed frame -- drop it, keep the connection alive.
        }
      }

      socket.onclose = () => {
        if (stopped) return
        setStatus("closed")
        scheduleReconnect()
      }

      socket.onerror = () => {
        socket?.close()
      }
    }

    connect()

    return () => {
      stopped = true
      if (reconnectTimer !== undefined) {
        clearTimeout(reconnectTimer)
      }
      socket?.close()
    }
  }, [url, enabled, baseDelayMs, maxDelayMs])

  return status
}
