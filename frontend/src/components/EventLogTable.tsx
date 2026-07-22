import { useMemo } from "react"
import { colorForMaterial } from "../telemetry/materialColors"
import type { TelemetryEvent } from "../telemetry/types"

interface EventLogTableProps {
  events: readonly TelemetryEvent[]
  maxRows?: number
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
}

export function EventLogTable({ events, maxRows = 25 }: EventLogTableProps) {
  const recent = useMemo(
    () =>
      [...events].sort((a, b) => b.occurred_at.localeCompare(a.occurred_at)).slice(0, maxRows),
    [events, maxRows],
  )

  return (
    <div className="max-h-96 overflow-y-auto rounded-lg border border-slate-200 dark:border-slate-800">
      <table className="w-full text-left text-sm">
        <thead className="sticky top-0 bg-slate-50 text-slate-500 dark:bg-slate-900 dark:text-slate-400">
          <tr>
            <th className="px-3 py-2 font-medium">Material</th>
            <th className="px-3 py-2 font-medium">Device</th>
            <th className="px-3 py-2 font-medium text-right">Confidence</th>
            <th className="px-3 py-2 font-medium text-right">Time</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {recent.map((event) => (
            <tr key={event.id} className="text-slate-700 dark:text-slate-200">
              <td className="px-3 py-1.5">
                <span className="inline-flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: colorForMaterial(event.material_type) }}
                    aria-hidden="true"
                  />
                  {event.material_type}
                </span>
              </td>
              <td className="px-3 py-1.5 text-slate-500 dark:text-slate-400">
                {event.device_id.slice(0, 8)}
              </td>
              <td className="px-3 py-1.5 text-right tabular-nums">
                {(event.confidence * 100).toFixed(1)}%
              </td>
              <td className="px-3 py-1.5 text-right tabular-nums text-slate-500 dark:text-slate-400">
                {formatTime(event.occurred_at)}
              </td>
            </tr>
          ))}
          {recent.length === 0 && (
            <tr>
              <td className="px-3 py-6 text-center text-slate-400" colSpan={4}>
                Waiting for events…
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
