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
