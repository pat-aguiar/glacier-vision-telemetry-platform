import type { Timestamped } from "./slidingWindowBuffer"

export interface MinuteBucket {
  /** ISO timestamp of the minute's start, e.g. "2026-07-21T15:24:00.000Z". */
  minute: string
  count: number
}

const MINUTE_MS = 60_000

function truncateToMinute(timestampMs: number): number {
  return Math.floor(timestampMs / MINUTE_MS) * MINUTE_MS
}

/**
 * Buckets events into events-per-minute counts. When a range is given (or
 * inferred from the data), every minute in between is emitted -- including
 * ones with zero events -- so a throughput chart shows a continuous
 * timeline instead of skipping quiet minutes.
 */
export function bucketEventsPerMinute(
  events: readonly Timestamped[],
  range?: { from: number; to: number },
): MinuteBucket[] {
  const counts = new Map<number, number>()

  for (const event of events) {
    const minute = truncateToMinute(new Date(event.occurred_at).getTime())
    counts.set(minute, (counts.get(minute) ?? 0) + 1)
  }

  let start: number
  let end: number
  if (range) {
    start = truncateToMinute(range.from)
    end = truncateToMinute(range.to)
  } else if (counts.size > 0) {
    const observed = [...counts.keys()]
    start = Math.min(...observed)
    end = Math.max(...observed)
  } else {
    return []
  }

  const buckets: MinuteBucket[] = []
  for (let minute = start; minute <= end; minute += MINUTE_MS) {
    buckets.push({ minute: new Date(minute).toISOString(), count: counts.get(minute) ?? 0 })
  }
  return buckets
}
