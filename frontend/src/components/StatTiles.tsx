import type { TelemetryEvent } from "../telemetry/types"

interface StatTilesProps {
  events: readonly TelemetryEvent[]
  windowMs: number
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
      <div className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-slate-900 dark:text-white">
        {value}
      </div>
    </div>
  )
}

export function StatTiles({ events, windowMs }: StatTilesProps) {
  const windowMinutes = windowMs / 60_000
  const eventsPerMinute = windowMinutes > 0 ? events.length / windowMinutes : 0
  const uniqueDevices = new Set(events.map((event) => event.device_id)).size
  const avgConfidence =
    events.length > 0
      ? events.reduce((sum, event) => sum + event.confidence, 0) / events.length
      : 0

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <Tile label="Active devices" value={String(uniqueDevices)} />
      <Tile label="Items / min" value={String(Math.round(eventsPerMinute))} />
      <Tile label="Avg confidence" value={`${(avgConfidence * 100).toFixed(1)}%`} />
    </div>
  )
}
