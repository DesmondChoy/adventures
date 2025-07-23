-- Backfill event_duration_seconds for choice_made events using timestamp differences
-- This calculates duration between consecutive choice events for the same adventure

WITH consecutive_events AS (
  SELECT 
    id,
    adventure_id,
    timestamp,
    LAG(timestamp) OVER (PARTITION BY adventure_id ORDER BY timestamp) as prev_timestamp,
    event_duration_seconds
  FROM telemetry_events 
  WHERE event_name = 'choice_made'
    AND event_duration_seconds IS NULL
),
calculated_durations AS (
  SELECT 
    id,
    CASE 
      WHEN prev_timestamp IS NOT NULL THEN 
        EXTRACT(EPOCH FROM (timestamp - prev_timestamp))
      ELSE NULL 
    END as calculated_duration
  FROM consecutive_events
)
UPDATE telemetry_events 
SET event_duration_seconds = calculated_durations.calculated_duration
FROM calculated_durations
WHERE telemetry_events.id = calculated_durations.id
  AND calculated_durations.calculated_duration IS NOT NULL
  AND calculated_durations.calculated_duration < 3600; -- Cap at 1 hour to filter out long idle times

-- Log the results
SELECT 
  COUNT(*) as updated_records,
  AVG(event_duration_seconds) as avg_duration_seconds,
  MAX(event_duration_seconds) as max_duration_seconds
FROM telemetry_events 
WHERE event_name = 'choice_made' 
  AND event_duration_seconds IS NOT NULL;
