ALTER TABLE public.telemetry_events
ADD COLUMN environment TEXT NULL DEFAULT 'unknown';

COMMENT ON COLUMN public.telemetry_events.environment IS 'The application environment where the event was generated (e.g., development, production).';
