import { useEffect, useMemo, useRef } from "react"
import {
  Chart,
  BarController,
  BarElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  type ChartConfiguration,
} from "chart.js"
import { usePrefersDarkMode } from "../hooks/usePrefersDarkMode"
import { bucketEventsPerMinute, type MinuteBucket } from "../telemetry/throughputAggregator"
import type { TelemetryEvent } from "../telemetry/types"

Chart.register(BarController, BarElement, LinearScale, CategoryScale, Tooltip)

interface RealTimeChartProps {
  events: readonly TelemetryEvent[]
  windowMs: number
}

function formatMinuteLabel(minuteIso: string): string {
  return new Date(minuteIso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
}

function buildConfig(
  buckets: MinuteBucket[],
  barColor: string,
  textColor: string,
  gridColor: string,
): ChartConfiguration<"bar"> {
  return {
    type: "bar",
    data: {
      labels: buckets.map((bucket) => formatMinuteLabel(bucket.minute)),
      datasets: [
        {
          label: "Items sorted / min",
          data: buckets.map((bucket) => bucket.count),
          backgroundColor: barColor,
          borderRadius: 4,
          maxBarThickness: 48,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: textColor },
        },
        y: {
          beginAtZero: true,
          grid: { color: gridColor },
          ticks: { color: textColor, precision: 0 },
        },
      },
      plugins: {
        tooltip: { enabled: true },
      },
    },
  }
}

export function RealTimeChart({ events, windowMs }: RealTimeChartProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const chartRef = useRef<Chart<"bar"> | null>(null)
  const prefersDark = usePrefersDarkMode()

  const buckets = useMemo(() => {
    const now = Date.now()
    return bucketEventsPerMinute(events, { from: now - windowMs, to: now })
  }, [events, windowMs])

  useEffect(() => {
    if (canvasRef.current === null) {
      return
    }

    const barColor = prefersDark ? "#3987e5" : "#2a78d6"
    const textColor = prefersDark ? "#c3c2b7" : "#52514e"
    const gridColor = prefersDark ? "#2c2c2a" : "#e1e0d9"
    const config = buildConfig(buckets, barColor, textColor, gridColor)

    if (chartRef.current === null) {
      chartRef.current = new Chart(canvasRef.current, config)
    } else {
      chartRef.current.data = config.data
      chartRef.current.options = config.options ?? {}
      chartRef.current.update()
    }
  }, [buckets, prefersDark])

  useEffect(
    () => () => {
      chartRef.current?.destroy()
      chartRef.current = null
    },
    [],
  )

  return (
    <div className="h-64 w-full">
      <canvas ref={canvasRef} role="img" aria-label="Items sorted per minute" />
    </div>
  )
}
