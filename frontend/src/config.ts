/**
 * Dynamically resolves the WebSocket URL for the telemetry live stream.
 *
 * In production, if served from the same server, it falls back to the current
 * host and adjusts the protocol (ws/wss) dynamically based on SSL/HTTPS.
 * In development, it defaults to the backend running on localhost:8000.
 *
 * This allows deploying the same build without hardcoding server hosts.
 */
function getTelemetryStreamUrl(): string {
  const envUrl = import.meta.env.VITE_TELEMETRY_STREAM_URL
  if (envUrl) {
    return envUrl
  }

  // Fallback behavior
  const isDev = import.meta.env.DEV
  if (isDev) {
    return "ws://localhost:8000/api/v1/telemetry/stream"
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
  return `${protocol}//${window.location.host}/api/v1/telemetry/stream`
}

export const TELEMETRY_STREAM_URL = getTelemetryStreamUrl()

/**
 * Same dev/prod fallback strategy as the stream URL above, but for plain
 * HTTP requests (e.g. fetching per-event image metadata).
 */
function getApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL
  if (envUrl) {
    return envUrl
  }

  const isDev = import.meta.env.DEV
  if (isDev) {
    return "http://localhost:8000"
  }

  return window.location.origin
}

export const API_BASE_URL = getApiBaseUrl()

/**
 * Dashboard auth token, baked into the bundle at build time (see
 * frontend/Dockerfile) since the browser has no other way to obtain it.
 * Sent as the `X-Dashboard-Token` header on HTTP requests and as a
 * `?token=` query param on the WebSocket connection (browsers can't set
 * custom headers on a WS handshake).
 */
export const DASHBOARD_ACCESS_TOKEN = import.meta.env.VITE_DASHBOARD_ACCESS_TOKEN ?? ""
