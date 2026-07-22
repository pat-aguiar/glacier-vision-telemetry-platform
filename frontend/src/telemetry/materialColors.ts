/** Curated colors for the material types the mock generator and real
 * sorters commonly report. Keys are matched case-insensitively.
 */
const MATERIAL_COLORS: Record<string, string> = {
  PET: "#3b82f6",
  HDPE: "#10b981",
  GLASS: "#06b6d4",
  ALUMINUM: "#94a3b8",
  CARDBOARD: "#b45309",
  STEEL: "#64748b",
  PP: "#a855f7",
  MIXED_PAPER: "#eab308",
}

/** Assigned by a stable hash to any material type not in the curated set,
 * so unrecognized materials still get a consistent color across renders.
 */
const FALLBACK_PALETTE = [
  "#ef4444",
  "#f97316",
  "#84cc16",
  "#14b8a6",
  "#6366f1",
  "#ec4899",
  "#22c55e",
  "#0ea5e9",
]

function hashString(value: string): number {
  let hash = 0
  for (let i = 0; i < value.length; i++) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0
  }
  return hash
}

/** Deterministic color for a material type: curated if known, otherwise a
 * stable hash-based pick from the fallback palette.
 */
export function colorForMaterial(materialType: string): string {
  const known = MATERIAL_COLORS[materialType.toUpperCase()]
  if (known) {
    return known
  }
  return FALLBACK_PALETTE[hashString(materialType) % FALLBACK_PALETTE.length]
}
