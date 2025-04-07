-- Add environment column to adventures table
ALTER TABLE public.adventures
ADD COLUMN environment TEXT NULL DEFAULT 'unknown';

-- Add comment for the new column
COMMENT ON COLUMN public.adventures.environment IS 'Indicates the environment where the adventure was created (e.g., development, production).';

-- Optional: Backfill existing rows if needed (unlikely for this project yet)
-- UPDATE public.adventures SET environment = 'production' WHERE environment IS NULL;
