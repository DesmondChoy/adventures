-- Add client_uuid column to adventures table
ALTER TABLE public.adventures
ADD COLUMN client_uuid TEXT NULL;

-- Add an index to the new client_uuid column for faster lookups
CREATE INDEX IF NOT EXISTS idx_adventures_client_uuid ON public.adventures (client_uuid);

-- Add a comment to the new column for documentation purposes
COMMENT ON COLUMN public.adventures.client_uuid IS 'Stores the client-generated UUID for session identification, used for resuming adventures.';
