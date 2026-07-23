import { useEffect, useRef, useState } from "react"
import { useEventImage } from "../hooks/useEventImage"
import { CONFIDENCE_LEGEND, colorForConfidence } from "../telemetry/confidenceColors"

interface ImageInspectorProps {
  /** The sorting event to show the captured frame for. `null` closes the drawer. */
  eventId: string | null
  onClose: () => void
}

export function ImageInspector({ eventId, onClose }: ImageInspectorProps) {
  const state = useEventImage(eventId)
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
  const closeButtonRef = useRef<HTMLButtonElement | null>(null)
  const isOpen = eventId !== null

  useEffect(() => {
    setHoveredIndex(null)
  }, [eventId])

  useEffect(() => {
    if (!isOpen) {
      return
    }

    closeButtonRef.current?.focus()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose()
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) {
    return null
  }

  const hoveredBox =
    state.status === "success" && hoveredIndex !== null
      ? state.data.bounding_boxes[hoveredIndex]
      : null

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label="Sorting event image inspector"
        className="relative flex h-full w-full max-w-lg flex-col gap-4 overflow-y-auto border-l border-slate-200 bg-white p-4 shadow-xl dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-slate-500 dark:text-slate-400">Event Image</h2>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
          >
            ✕
          </button>
        </div>

        {state.status === "loading" && (
          <p className="text-sm text-slate-500 dark:text-slate-400">Loading image…</p>
        )}

        {state.status === "error" && <p className="text-sm text-red-500">{state.error}</p>}

        {state.status === "success" && (
          <>
            <div className="relative w-full overflow-hidden rounded-lg border border-slate-200 dark:border-slate-800">
              <img
                src={state.data.image_url}
                alt="Captured sorting event frame"
                className="block w-full"
              />
              <svg
                viewBox="0 0 1 1"
                preserveAspectRatio="none"
                className="absolute inset-0 h-full w-full"
              >
                {state.data.bounding_boxes.map((box, index) => (
                  <rect
                    key={`${box.label}-${index}`}
                    x={box.x_min}
                    y={box.y_min}
                    width={box.x_max - box.x_min}
                    height={box.y_max - box.y_min}
                    fill="transparent"
                    stroke={colorForConfidence(box.confidence)}
                    strokeWidth={2}
                    vectorEffect="non-scaling-stroke"
                    className="cursor-pointer"
                    onMouseEnter={() => setHoveredIndex(index)}
                    onMouseLeave={() =>
                      setHoveredIndex((current) => (current === index ? null : current))
                    }
                  />
                ))}
              </svg>

              {hoveredBox && (
                <div
                  className="pointer-events-none absolute -translate-y-full rounded bg-slate-900 px-2 py-1 text-xs whitespace-nowrap text-white shadow dark:bg-slate-100 dark:text-slate-900"
                  style={{ left: `${hoveredBox.x_min * 100}%`, top: `${hoveredBox.y_min * 100}%` }}
                >
                  {hoveredBox.label} — {(hoveredBox.confidence * 100).toFixed(0)}%
                </div>
              )}
            </div>

            <div className="flex flex-wrap gap-3 text-xs text-slate-500 dark:text-slate-400">
              {CONFIDENCE_LEGEND.map((tier) => (
                <span key={tier.tier} className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: tier.color }}
                    aria-hidden="true"
                  />
                  {tier.label}
                </span>
              ))}
            </div>

            <ul className="flex flex-col gap-1 text-sm text-slate-700 dark:text-slate-200">
              {state.data.bounding_boxes.map((box, index) => (
                <li key={`${box.label}-${index}`} className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: colorForConfidence(box.confidence) }}
                      aria-hidden="true"
                    />
                    {box.label}
                  </span>
                  <span className="tabular-nums text-slate-500 dark:text-slate-400">
                    {(box.confidence * 100).toFixed(0)}%
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  )
}
