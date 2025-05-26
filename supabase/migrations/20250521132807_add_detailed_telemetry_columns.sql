-- Add chapter_type column
ALTER TABLE public.telemetry_events
ADD COLUMN chapter_type TEXT NULL;

COMMENT ON COLUMN public.telemetry_events.chapter_type IS 'The type of chapter the event relates to (e.g., story, lesson, reflect, conclusion, summary).';

-- Add chapter_number column
ALTER TABLE public.telemetry_events
ADD COLUMN chapter_number INTEGER NULL;

COMMENT ON COLUMN public.telemetry_events.chapter_number IS 'The specific chapter number within the adventure that this event pertains to.';

-- Add event_duration_ms column
ALTER TABLE public.telemetry_events
ADD COLUMN event_duration_ms INTEGER NULL;

COMMENT ON COLUMN public.telemetry_events.event_duration_ms IS 'For events like choice_made, this can store the duration (in milliseconds) spent on the preceding chapter. For other events, it might be NULL or represent event processing time.';
