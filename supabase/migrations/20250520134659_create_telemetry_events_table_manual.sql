-- Migration to define the telemetry_events table and ensure its schema matches requirements.
-- This migration assumes the table might have been partially created via the Supabase dashboard.

-- Create the table if it doesn't exist (idempotent)
CREATE TABLE IF NOT EXISTS public.telemetry_events (
    id BIGSERIAL PRIMARY KEY,
    event_name TEXT, -- Will be altered to NOT NULL
    adventure_id UUID NULL,
    user_id UUID NULL, -- For future authentication integration
    "timestamp" TIMESTAMPTZ DEFAULT now(), -- Will be altered to NOT NULL
    metadata JSONB NULL
);

-- Alter columns to add NOT NULL constraints if they are missing
-- Note: If these columns already have data with NULLs where NOT NULL is required,
-- these ALTER statements might fail. Ensure data is clean or handle NULLs before applying.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'telemetry_events' AND column_name = 'event_name' AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE public.telemetry_events ALTER COLUMN event_name SET NOT NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'telemetry_events' AND column_name = 'timestamp' AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE public.telemetry_events ALTER COLUMN "timestamp" SET NOT NULL;
    END IF;
END $$;

-- Add foreign key constraint if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fk_telemetry_adventure_to_adventures' AND conrelid = 'public.telemetry_events'::regclass
    ) THEN
        ALTER TABLE public.telemetry_events
        ADD CONSTRAINT fk_telemetry_adventure_to_adventures
            FOREIGN KEY(adventure_id) 
            REFERENCES public.adventures(id)
            ON DELETE SET NULL; -- Or ON DELETE CASCADE if preferred
    END IF;
END $$;

-- Add comments to describe the table and columns
COMMENT ON TABLE public.telemetry_events IS 'Stores telemetry events for user interactions and system events.';
COMMENT ON COLUMN public.telemetry_events.id IS 'Unique identifier for the telemetry event.';
COMMENT ON COLUMN public.telemetry_events.event_name IS 'Name of the event (e.g., adventure_started, chapter_viewed).';
COMMENT ON COLUMN public.telemetry_events.adventure_id IS 'Foreign key referencing the adventure this event is associated with, if any.';
COMMENT ON COLUMN public.telemetry_events.user_id IS 'Foreign key referencing the user this event is associated with, if authentication is implemented.';
COMMENT ON COLUMN public.telemetry_events.timestamp IS 'Timestamp of when the event occurred.';
COMMENT ON COLUMN public.telemetry_events.metadata IS 'JSONB field to store event-specific details.';

-- Add indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_telemetry_event_name ON public.telemetry_events(event_name);
CREATE INDEX IF NOT EXISTS idx_telemetry_adventure_id ON public.telemetry_events(adventure_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON public.telemetry_events("timestamp");
