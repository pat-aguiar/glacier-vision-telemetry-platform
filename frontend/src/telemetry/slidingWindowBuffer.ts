/** Anything with a server-assigned occurrence timestamp can live in a buffer. */
export interface Timestamped {
  occurred_at: string
}

/**
 * Keeps only the items whose `occurred_at` falls within the last `windowMs`
 * of "now". Used to feed live charts a rolling slice of telemetry without
 * the caller having to re-filter the full event history on every render.
 */
export class SlidingWindowBuffer<T extends Timestamped> {
  private items: T[] = []
  private readonly windowMs: number

  constructor(windowMs: number) {
    if (windowMs <= 0) {
      throw new Error("windowMs must be positive")
    }
    this.windowMs = windowMs
  }

  /** Add an item, then drop anything that has aged out of the window. */
  push(item: T, now: number = Date.now()): void {
    this.items.push(item)
    this.evict(now)
  }

  /** Drop items older than the window without adding anything new. */
  evict(now: number = Date.now()): void {
    const cutoff = now - this.windowMs
    // A plain filter (rather than trimming from the front) stays correct
    // even if items arrive slightly out of occurred_at order over the wire.
    this.items = this.items.filter((item) => new Date(item.occurred_at).getTime() >= cutoff)
  }

  getAll(): readonly T[] {
    return this.items
  }

  clear(): void {
    this.items = []
  }

  get size(): number {
    return this.items.length
  }
}
