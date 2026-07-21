import { act, renderHook } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { usePrefersDarkMode } from "./usePrefersDarkMode"

class FakeMediaQueryList {
  matches: boolean
  private listeners = new Set<(event: { matches: boolean }) => void>()

  constructor(matches: boolean) {
    this.matches = matches
  }

  addEventListener(_type: "change", listener: (event: { matches: boolean }) => void): void {
    this.listeners.add(listener)
  }

  removeEventListener(_type: "change", listener: (event: { matches: boolean }) => void): void {
    this.listeners.delete(listener)
  }

  setMatches(matches: boolean): void {
    this.matches = matches
    for (const listener of this.listeners) {
      listener({ matches })
    }
  }

  get listenerCount(): number {
    return this.listeners.size
  }
}

function stubMatchMedia(initialMatches: boolean): FakeMediaQueryList {
  const mediaQueryList = new FakeMediaQueryList(initialMatches)
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockReturnValue(mediaQueryList),
  )
  return mediaQueryList
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("usePrefersDarkMode", () => {
  it("reflects the initial OS preference", () => {
    stubMatchMedia(true)
    const { result } = renderHook(() => usePrefersDarkMode())
    expect(result.current).toBe(true)
  })

  it("updates live when the OS preference changes", () => {
    const mediaQueryList = stubMatchMedia(false)
    const { result } = renderHook(() => usePrefersDarkMode())

    expect(result.current).toBe(false)

    act(() => mediaQueryList.setMatches(true))
    expect(result.current).toBe(true)

    act(() => mediaQueryList.setMatches(false))
    expect(result.current).toBe(false)
  })

  it("unsubscribes from the media query on unmount", () => {
    const mediaQueryList = stubMatchMedia(false)
    const { unmount } = renderHook(() => usePrefersDarkMode())

    expect(mediaQueryList.listenerCount).toBeGreaterThan(0)
    unmount()
    expect(mediaQueryList.listenerCount).toBe(0)
  })
})
