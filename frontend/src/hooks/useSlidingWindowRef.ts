import { useEffect, useRef } from "react"
import { SlidingWindowBuffer, type Timestamped } from "../telemetry/slidingWindowBuffer"

const DEFAULT_EVICT_INTERVAL_MS = 1_000

/**
 * Holds a SlidingWindowBuffer in a ref so pushing new items never itself
 * triggers a re-render -- pair with something like useThrottledState to
 * control how often consumers actually re-render off the buffer's contents.
 *
 * Also evicts on a timer, independent of pushes, so the window stays
 * accurate to wall-clock time even if the event stream goes quiet.
 */
export function useSlidingWindowRef<T extends Timestamped>(
  windowMs: number,
  evictIntervalMs: number = DEFAULT_EVICT_INTERVAL_MS,
): SlidingWindowBuffer<T> {
  const bufferRef = useRef<SlidingWindowBuffer<T> | null>(null)
  if (bufferRef.current === null) {
    bufferRef.current = new SlidingWindowBuffer<T>(windowMs)
  }
  const buffer = bufferRef.current

  useEffect(() => {
    const timer = setInterval(() => buffer.evict(), evictIntervalMs)
    return () => clearInterval(timer)
  }, [buffer, evictIntervalMs])

  return buffer
}
