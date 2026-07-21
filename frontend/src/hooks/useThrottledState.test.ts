import { act, renderHook } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { useThrottledState } from "./useThrottledState"

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe("useThrottledState", () => {
  it("flushes the first update immediately (leading edge)", () => {
    const { result } = renderHook(() => useThrottledState(0, 300))

    act(() => result.current[1](1))

    expect(result.current[0]).toBe(1)
  })

  it("coalesces rapid updates into a single trailing flush per interval", () => {
    const { result } = renderHook(() => useThrottledState(0, 300))

    act(() => result.current[1](1)) // leading flush -> 1
    expect(result.current[0]).toBe(1)

    act(() => {
      result.current[1](2)
      result.current[1](3)
      result.current[1](4)
    })
    // still 1 -- none of these should render synchronously
    expect(result.current[0]).toBe(1)

    act(() => {
      vi.advanceTimersByTime(299)
    })
    expect(result.current[0]).toBe(1)

    act(() => {
      vi.advanceTimersByTime(1)
    })
    expect(result.current[0]).toBe(4) // last pending value, intermediate ones dropped
  })

  it("supports functional updaters against the latest pending value", () => {
    const { result } = renderHook(() => useThrottledState(0, 300))

    act(() => result.current[1]((prev) => prev + 1)) // leading -> 1
    act(() => {
      result.current[1]((prev) => prev + 1)
      result.current[1]((prev) => prev + 1)
    })

    act(() => {
      vi.advanceTimersByTime(300)
    })
    expect(result.current[0]).toBe(3)
  })

  it("flushes leading-edge again after a quiet period past the interval", () => {
    const { result } = renderHook(() => useThrottledState(0, 300))

    act(() => result.current[1](1))
    act(() => {
      vi.advanceTimersByTime(500) // well past the interval, no pending updates
    })

    act(() => result.current[1](2))
    expect(result.current[0]).toBe(2) // immediate again, no 300ms wait needed
  })
})
