import { act, renderHook } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { useSlidingWindowRef } from "./useSlidingWindowRef"
import type { Timestamped } from "../telemetry/slidingWindowBuffer"

interface Event extends Timestamped {
  seq: number
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe("useSlidingWindowRef", () => {
  it("returns a stable buffer instance across re-renders", () => {
    const { result, rerender } = renderHook(() => useSlidingWindowRef<Event>(60_000))

    const first = result.current
    rerender()
    expect(result.current).toBe(first)
  })

  it("pushing does not require a re-render to be reflected in getAll()", () => {
    const { result } = renderHook(() => useSlidingWindowRef<Event>(60_000))

    act(() => {
      result.current.push({ seq: 1, occurred_at: new Date().toISOString() })
    })

    expect(result.current.getAll()).toHaveLength(1)
  })

  it("evicts stale items on a timer even without new pushes", () => {
    const windowMs = 5_000
    const { result } = renderHook(() => useSlidingWindowRef<Event>(windowMs, 1_000))

    act(() => {
      result.current.push({ seq: 1, occurred_at: new Date().toISOString() })
    })
    expect(result.current.size).toBe(1)

    act(() => {
      vi.advanceTimersByTime(windowMs + 1_000)
    })

    expect(result.current.size).toBe(0)
  })

  it("clears its eviction timer on unmount", () => {
    const clearIntervalSpy = vi.spyOn(globalThis, "clearInterval")
    const { unmount } = renderHook(() => useSlidingWindowRef<Event>(60_000))

    unmount()

    expect(clearIntervalSpy).toHaveBeenCalled()
  })
})
