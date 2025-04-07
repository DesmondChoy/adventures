-- Create adventures table for storing adventure state data
CREATE TABLE public.adventures (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NULL, -- Link to auth.users later if Auth is implemented
    state_data jsonb NOT NULL,
    story_category text NULL,
    lesson_topic text NULL,
    is_complete boolean NOT NULL DEFAULT false,
    completed_chapter_count integer NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
    -- CONSTRAINT adventures_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE SET NULL
    -- Uncomment the above line when implementing Auth
);

-- Trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_adventures_updated
  BEFORE UPDATE ON public.adventures
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();

-- Enable RLS (Row Level Security) for the table
ALTER TABLE public.adventures ENABLE ROW LEVEL SECURITY;

-- Initially, we'll create a policy that allows backend access via service key
-- This can be refined later when implementing user-specific access
CREATE POLICY "Allow service_role access" ON public.adventures
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- Grant permissions (adjust based on your access patterns)
-- Grant all permissions to the service_role (backend)
GRANT ALL ON TABLE public.adventures TO service_role;
-- Grant select permissions to authenticated users (if frontend needs read access)
-- GRANT SELECT ON TABLE public.adventures TO authenticated;
-- Grant select permissions to anon users (if public read access needed)
-- GRANT SELECT ON TABLE public.adventures TO anon;

-- Add table and column comments for documentation
COMMENT ON TABLE public.adventures IS 'Stores the state and metadata of user adventures.';
COMMENT ON COLUMN public.adventures.id IS 'Unique identifier for the adventure.';
COMMENT ON COLUMN public.adventures.user_id IS 'Foreign key linking to the user who created the adventure (if authenticated).';
COMMENT ON COLUMN public.adventures.state_data IS 'Complete JSONB representation of the AdventureState.';
COMMENT ON COLUMN public.adventures.story_category IS 'The category of the story chosen by the user.';
COMMENT ON COLUMN public.adventures.lesson_topic IS 'The educational topic chosen by the user.';
COMMENT ON COLUMN public.adventures.is_complete IS 'Flag indicating if the adventure has reached its conclusion.';
COMMENT ON COLUMN public.adventures.completed_chapter_count IS 'Number of chapters completed in the adventure.';
COMMENT ON COLUMN public.adventures.created_at IS 'Timestamp when the adventure was first created.';
COMMENT ON COLUMN public.adventures.updated_at IS 'Timestamp when the adventure was last updated.';
