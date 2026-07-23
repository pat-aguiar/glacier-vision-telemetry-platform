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

/** Mirrors `BoundingBox` in app/schemas.py -- coordinates are normalized to
 * the captured frame's dimensions (0.0 = left/top edge, 1.0 = right/bottom).
 */
export interface BoundingBox {
  label: string
  confidence: number
  x_min: number
  y_min: number
  x_max: number
  y_max: number
}

/** Mirrors `TelemetryEventImageRead` in app/schemas.py -- the shape returned
 * by `GET /api/v1/telemetry/events/{event_id}/image`.
 */
export interface TelemetryEventImage {
  image_url: string
  bounding_boxes: BoundingBox[]
}
