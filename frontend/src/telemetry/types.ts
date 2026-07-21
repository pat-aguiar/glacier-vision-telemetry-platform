/** Mirrors `SortingEventRead` in app/schemas.py -- the shape returned by
 * `POST /api/v1/telemetry/events` and broadcast over `/api/v1/telemetry/stream`.
 */
export interface TelemetryEvent {
  id: string
  device_id: string
  facility_id: string
  occurred_at: string
  material_type: string
  confidence: number
  payload: Record<string, unknown> | null
  event_id: string | null
  created_at: string
}
