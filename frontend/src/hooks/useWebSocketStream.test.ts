import { act, renderHook } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { useWebSocketStream } from "./useWebSocketStream"

class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  url: string
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  closeCalls = 0

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  close(): void {
    this.closeCalls += 1
  }

  triggerOpen(): void {
    this.onopen?.()
  }

  triggerMessage(data: unknown): void {
    this.onmessage?.({ data: JSON.stringify(data) })
  }

  triggerRawMessage(data: string): void {
    this.onmessage?.({ data })
  }

  triggerClose(): void {
    this.onclose?.()
  }
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.spyOn(Math, "random").mockReturnValue(0) // pin jitter to the low end of its range
  FakeWebSocket.instances = []
  vi.stubGlobal("WebSocket", FakeWebSocket)
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe("useWebSocketStream", () => {
  it("connects, reports open, and delivers parsed messages", () => {
    const onMessage = vi.fn()
    const { result } = renderHook(() =>
      useWebSocketStream<{ seq: number }>("ws://api/stream", { onMessage }),
    )

    expect(result.current).toBe("connecting")
    expect(FakeWebSocket.instances).toHaveLength(1)

    act(() => FakeWebSocket.instances[0].triggerOpen())
    expect(result.current).toBe("open")

    act(() => FakeWebSocket.instances[0].triggerMessage({ seq: 1 }))
    expect(onMessage).toHaveBeenCalledWith({ seq: 1 })
  })

  it("ignores malformed frames instead of throwing", () => {
    const onMessage = vi.fn()
    renderHook(() => useWebSocketStream("ws://api/stream", { onMessage }))

    expect(() => {
      act(() => FakeWebSocket.instances[0].triggerRawMessage("not json"))
    }).not.toThrow()
    expect(onMessage).not.toHaveBeenCalled()
  })

  it("reconnects with exponential backoff after a close, and resets on reopen", () => {
    const onMessage = vi.fn()
    const { result } = renderHook(() =>
      useWebSocketStream("ws://api/stream", { onMessage, baseDelayMs: 1000, maxDelayMs: 8000 }),
    )

    act(() => FakeWebSocket.instances[0].triggerOpen())
    expect(result.current).toBe("open")

    // First disconnect: backoff attempt 0 -> base delay (jitter pinned to 0.5x).
    act(() => FakeWebSocket.instances[0].triggerClose())
    expect(result.current).toBe("closed")
    expect(FakeWebSocket.instances).toHaveLength(1)

    act(() => {
      vi.advanceTimersByTime(499)
    })
    expect(FakeWebSocket.instances).toHaveLength(1) // not yet

    act(() => {
      vi.advanceTimersByTime(1)
    })
    expect(FakeWebSocket.instances).toHaveLength(2)
    expect(result.current).toBe("reconnecting")

    // Second disconnect without a successful reopen: backoff attempt 1 -> 2x base delay.
    act(() => FakeWebSocket.instances[1].triggerClose())
    act(() => {
      vi.advanceTimersByTime(999) // 2000 * 0.5 - 1
    })
    expect(FakeWebSocket.instances).toHaveLength(2)
    act(() => {
      vi.advanceTimersByTime(1)
    })
    expect(FakeWebSocket.instances).toHaveLength(3)

    // A successful open resets the backoff counter back to base delay.
    act(() => FakeWebSocket.instances[2].triggerOpen())
    expect(result.current).toBe("open")

    act(() => FakeWebSocket.instances[2].triggerClose())
    act(() => {
      vi.advanceTimersByTime(499)
    })
    expect(FakeWebSocket.instances).toHaveLength(3)
    act(() => {
      vi.advanceTimersByTime(1)
    })
    expect(FakeWebSocket.instances).toHaveLength(4)
  })

  it("closes the socket and stops reconnecting on unmount", () => {
    const onMessage = vi.fn()
    const { unmount } = renderHook(() => useWebSocketStream("ws://api/stream", { onMessage }))

    const socket = FakeWebSocket.instances[0]
    unmount()

    expect(socket.closeCalls).toBe(1)

    act(() => {
      vi.advanceTimersByTime(60_000)
    })
    expect(FakeWebSocket.instances).toHaveLength(1) // no reconnect after unmount
  })
})
