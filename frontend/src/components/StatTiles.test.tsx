import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { StatTiles } from "./StatTiles"
import type { TelemetryEvent } from "../telemetry/types"

function makeEvent(overrides: Partial<TelemetryEvent>): TelemetryEvent {
  return {
    id: "id-1",
    device_id: "device-1",
    facility_id: "facility-1",
    occurred_at: "2026-01-01T00:00:00Z",
    material_type: "plastic",
    confidence: 0.9,
    payload: null,
    event_id: null,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  }
}

describe("StatTiles", () => {
  it("renders device count, events per minute, and formatted avg confidence", () => {
    const events: TelemetryEvent[] = [
      makeEvent({ device_id: "device-1", confidence: 0.8 }),
      makeEvent({ device_id: "device-2", confidence: 0.9 }),
      makeEvent({ device_id: "device-1", confidence: 1.0 }),
    ]

    render(<StatTiles events={events} windowMs={60_000} />)

    expect(screen.getByText("Active devices")).toBeInTheDocument()
    expect(screen.getByText("2")).toBeInTheDocument()

    expect(screen.getByText("Items / min")).toBeInTheDocument()
    expect(screen.getByText("3")).toBeInTheDocument()

    expect(screen.getByText("Avg confidence")).toBeInTheDocument()
    expect(screen.getByText("90.0%")).toBeInTheDocument()
  })
})
