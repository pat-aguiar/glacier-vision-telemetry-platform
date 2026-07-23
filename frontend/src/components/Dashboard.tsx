import { useEffect, useState } from "react"
import { useWebSocketStream, type ConnectionStatus } from "../hooks/useWebSocketStream"
import { useSlidingWindowRef } from "../hooks/useSlidingWindowRef"
import { useThrottledState } from "../hooks/useThrottledState"
import { StatTiles } from "./StatTiles"
import { RealTimeChart } from "./RealTimeChart"
import { EventLogTable } from "./EventLogTable"
import { ImageInspector } from "./ImageInspector"
import { TELEMETRY_STREAM_URL } from "../config"
import type { TelemetryEvent } from "../telemetry/types"

const WINDOW_MS = 5 * 60_000
const THROTTLE_MS = 300

const STATUS_STYLES: Record<ConnectionStatus, string> = {
  open: "bg-green-500",
  connecting: "bg-amber-500",
  reconnecting: "bg-amber-500",
  closed: "bg-red-500",
}

const STATUS_LABEL: Record<ConnectionStatus, string> = {
  open: "Connected",
  connecting: "Connecting…",
  reconnecting: "Reconnecting…",
  closed: "Disconnected — retrying",
}

function ConnectionBadge({ status }: { status: ConnectionStatus }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
      <span className={`h-2 w-2 rounded-full ${STATUS_STYLES[status]}`} aria-hidden="true" />
      {STATUS_LABEL[status]}
    </span>
  )
}

export function Dashboard() {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const buffer = useSlidingWindowRef<TelemetryEvent>(WINDOW_MS)
  const [events, setEvents] = useThrottledState<readonly TelemetryEvent[]>(
    buffer.getAll(),
    THROTTLE_MS,
  )

  const status = useWebSocketStream<TelemetryEvent>(TELEMETRY_STREAM_URL, {
    onMessage: (event) => {
      buffer.push(event)
      setEvents(buffer.getAll())
    },
  })

  // Forces a render on the same cadence even without new messages, so the
  // window visibly decays (old events drop off) during quiet periods
  // instead of only updating on the next arrival.
  useEffect(() => {
    const timer = setInterval(() => {
      buffer.evict()
      setEvents(buffer.getAll())
    }, THROTTLE_MS)
    return () => clearInterval(timer)
  }, [buffer, setEvents])

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
          Sorting Telemetry
        </h1>
        <ConnectionBadge status={status} />
      </div>

      <StatTiles events={events} windowMs={WINDOW_MS} />

      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-3 text-sm font-medium text-slate-500 dark:text-slate-400">
          Items sorted per minute (last 5 minutes)
        </h2>
        <RealTimeChart events={events} windowMs={WINDOW_MS} />
      </div>

      <div>
        <h2 className="mb-3 text-sm font-medium text-slate-500 dark:text-slate-400">
          Recent events
        </h2>
        <EventLogTable
          events={events}
          selectedEventId={selectedEventId}
          onSelectEvent={(event) => setSelectedEventId(event.id)}
        />
      </div>

      <ImageInspector eventId={selectedEventId} onClose={() => setSelectedEventId(null)} />
    </div>
  )
}
