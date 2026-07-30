/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_TELEMETRY_STREAM_URL?: string
  readonly VITE_API_BASE_URL?: string
  readonly VITE_DASHBOARD_ACCESS_TOKEN?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
