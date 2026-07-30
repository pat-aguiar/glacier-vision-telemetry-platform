import { useEffect, useState } from "react"
import { API_BASE_URL, DASHBOARD_ACCESS_TOKEN } from "../config"
import type { TelemetryEventImage } from "../telemetry/types"

export type EventImageState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; error: string }
  | { status: "success"; data: TelemetryEventImage }

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError"
}

async function fetchEventImage(
  eventId: string,
  signal: AbortSignal,
): Promise<TelemetryEventImage> {
  const response = await fetch(`${API_BASE_URL}/api/v1/telemetry/events/${eventId}/image`, {
    signal,
    headers: { "X-Dashboard-Token": DASHBOARD_ACCESS_TOKEN },
  })

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const message =
      body !== null &&
      typeof body === "object" &&
      "error" in body &&
      typeof (body as { error?: { message?: unknown } }).error?.message === "string"
        ? (body as { error: { message: string } }).error.message
        : `Request failed with status ${response.status}`
    throw new Error(message)
  }

  return (await response.json()) as TelemetryEventImage
}

/**
 * Fetches image metadata (mock image URL + bounding boxes) for a sorting
 * event. Pass `null` when no event is selected yet.
 *
 * Cancels the in-flight request via AbortController whenever `eventId`
 * changes or the component unmounts, so a slow response for a
 * since-abandoned event id can never clobber state for the current one.
 */
export function useEventImage(eventId: string | null): EventImageState {
  const [state, setState] = useState<EventImageState>({ status: "idle" })

  useEffect(() => {
    if (eventId === null) {
      setState({ status: "idle" })
      return
    }

    const controller = new AbortController()
    setState({ status: "loading" })

    fetchEventImage(eventId, controller.signal)
      .then((data) => {
        setState({ status: "success", data })
      })
      .catch((error: unknown) => {
        if (isAbortError(error)) {
          return
        }
        const message = error instanceof Error ? error.message : "Failed to load event image"
        setState({ status: "error", error: message })
      })

    return () => {
      controller.abort()
    }
  }, [eventId])

  return state
}
