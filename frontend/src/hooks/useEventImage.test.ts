import { act, renderHook } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { useEventImage } from "./useEventImage"

interface FakeResponse {
  ok: boolean
  status: number
  json: () => Promise<unknown>
}

interface PendingFetch {
  signal: AbortSignal
  resolve: (value: FakeResponse) => void
  reject: (reason?: unknown) => void
}

function installFakeFetch(): PendingFetch[] {
  const pending: PendingFetch[] = []

  const fakeFetch = vi.fn((_url: string, init?: { signal?: AbortSignal }) => {
    let resolve!: PendingFetch["resolve"]
    let reject!: PendingFetch["reject"]
    const promise = new Promise<FakeResponse>((res, rej) => {
      resolve = res
      reject = rej
    })

    const signal = init?.signal ?? new AbortController().signal
    signal.addEventListener("abort", () => {
      reject(new DOMException("Aborted", "AbortError"))
    })

    pending.push({ signal, resolve, reject })
    return promise
  })

  vi.stubGlobal("fetch", fakeFetch)
  return pending
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("useEventImage", () => {
  it("is idle when eventId is null", () => {
    const { result } = renderHook(() => useEventImage(null))
    expect(result.current).toEqual({ status: "idle" })
  })

  it("transitions loading -> success on a 200 response", async () => {
    const pending = installFakeFetch()
    const { result } = renderHook(() => useEventImage("event-1"))

    expect(result.current).toEqual({ status: "loading" })
    expect(pending).toHaveLength(1)

    const data = { image_url: "/static/x.jpg", bounding_boxes: [] }
    await act(async () => {
      pending[0].resolve({ ok: true, status: 200, json: async () => data })
    })

    expect(result.current).toEqual({ status: "success", data })
  })

  it("transitions loading -> error using the backend error envelope message", async () => {
    const pending = installFakeFetch()
    const { result } = renderHook(() => useEventImage("missing-event"))

    await act(async () => {
      pending[0].resolve({
        ok: false,
        status: 404,
        json: async () => ({
          error: {
            code: "sorting_event_not_found",
            message: "No sorting event found with id 'missing-event'.",
          },
        }),
      })
    })

    expect(result.current).toEqual({
      status: "error",
      error: "No sorting event found with id 'missing-event'.",
    })
  })

  it("transitions loading -> error on network failure", async () => {
    const pending = installFakeFetch()
    const { result } = renderHook(() => useEventImage("event-1"))

    await act(async () => {
      pending[0].reject(new TypeError("Failed to fetch"))
    })

    expect(result.current).toEqual({ status: "error", error: "Failed to fetch" })
  })

  it("aborts the in-flight request when eventId changes", () => {
    const pending = installFakeFetch()
    const { rerender } = renderHook(({ eventId }) => useEventImage(eventId), {
      initialProps: { eventId: "event-1" },
    })

    const firstRequest = pending[0]
    expect(firstRequest.signal.aborted).toBe(false)

    rerender({ eventId: "event-2" })

    expect(firstRequest.signal.aborted).toBe(true)
    expect(pending).toHaveLength(2)
  })

  it("does not let a stale, aborted request's rejection surface as a visible error", async () => {
    const pending = installFakeFetch()
    const { result, rerender } = renderHook(({ eventId }) => useEventImage(eventId), {
      initialProps: { eventId: "event-1" },
    })

    rerender({ eventId: "event-2" })
    expect(result.current).toEqual({ status: "loading" })

    const secondData = { image_url: "/static/two.jpg", bounding_boxes: [] }
    await act(async () => {
      pending[1].resolve({ ok: true, status: 200, json: async () => secondData })
    })

    expect(result.current).toEqual({ status: "success", data: secondData })
  })

  it("aborts the in-flight request on unmount", () => {
    const pending = installFakeFetch()
    const { unmount } = renderHook(() => useEventImage("event-1"))

    const request = pending[0]
    expect(request.signal.aborted).toBe(false)

    unmount()

    expect(request.signal.aborted).toBe(true)
  })
})
