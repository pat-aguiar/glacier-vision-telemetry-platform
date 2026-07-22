export type ConfidenceTier = "low" | "medium" | "high" | "very-high"

export interface ConfidenceTierInfo {
  tier: ConfidenceTier
  label: string
  color: string
  /** Inclusive lower bound of this tier, on a 0.0-1.0 confidence scale. */
  minConfidence: number
}

/** Highest confidence first -- also the order a legend should render in. */
const CONFIDENCE_TIERS: readonly ConfidenceTierInfo[] = [
  { tier: "very-high", label: "Very High", color: "#22c55e", minConfidence: 0.9 },
  { tier: "high", label: "High", color: "#84cc16", minConfidence: 0.75 },
  { tier: "medium", label: "Medium", color: "#f59e0b", minConfidence: 0.5 },
  { tier: "low", label: "Low", color: "#ef4444", minConfidence: 0 },
]

/** Legend entries for a confidence color key, highest tier first. */
export const CONFIDENCE_LEGEND: readonly ConfidenceTierInfo[] = CONFIDENCE_TIERS

/** Classifies a 0.0-1.0 confidence value into one of the 4 tiers above. */
export function confidenceTierFor(confidence: number): ConfidenceTierInfo {
  const tier = CONFIDENCE_TIERS.find((entry) => confidence >= entry.minConfidence)
  return tier ?? CONFIDENCE_TIERS[CONFIDENCE_TIERS.length - 1]
}

export function colorForConfidence(confidence: number): string {
  return confidenceTierFor(confidence).color
}
