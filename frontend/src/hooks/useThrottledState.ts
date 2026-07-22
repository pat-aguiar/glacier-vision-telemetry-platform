import { useCallback, useEffect, useRef, useState } from "react"

export type ThrottledSetState<T> = (updater: T | ((prev: T) => T)) => void

/**
 * Like useState, but re-renders are coalesced to at most once per
 * `intervalMs`. The first update in a quiet period flushes immediately
 * (leading edge); rapid updates after that are merged and flushed together
 * on the next interval boundary (trailing edge), so a fast producer (e.g.
 * a websocket firing many messages per second) can't force a render per
 * message.
 */
export function useThrottledState<T>(
  initialValue: T,
  intervalMs = 300,
): [T, ThrottledSetState<T>] {
  const [state, setState] = useState(initialValue)
  const pendingRef = useRef(initialValue)
  const lastFlushRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  const flush = useCallback(() => {
    timerRef.current = undefined
    lastFlushRef.current = Date.now()
    setState(pendingRef.current)
  }, [])

  const setThrottled = useCallback<ThrottledSetState<T>>(
    (updater) => {
      pendingRef.current =
        typeof updater === "function" ? (updater as (prev: T) => T)(pendingRef.current) : updater

      const elapsed = Date.now() - lastFlushRef.current
      if (elapsed >= intervalMs) {
        flush()
      } else if (timerRef.current === undefined) {
        timerRef.current = setTimeout(flush, intervalMs - elapsed)
      }
    },
    [flush, intervalMs],
  )

  useEffect(
    () => () => {
      if (timerRef.current !== undefined) {
        clearTimeout(timerRef.current)
      }
    },
    [],
  )

  return [state, setThrottled]
}
