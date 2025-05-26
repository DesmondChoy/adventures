-- Rename the existing event_duration_ms column to event_duration_seconds
ALTER TABLE public.telemetry_events
RENAME COLUMN event_duration_ms TO event_duration_seconds;

-- Update the comment on the column to reflect the new unit
COMMENT ON COLUMN public.telemetry_events.event_duration_seconds IS 'For events like choice_made, this can store the duration (in seconds) spent on the preceding chapter. For other events, it might be NULL or represent event processing time.';
