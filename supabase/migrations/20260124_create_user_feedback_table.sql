-- Create user_feedback table for collecting user feedback on adventures
-- This supports the "once per user" feedback prompt at chapter 5

CREATE TABLE IF NOT EXISTS public.user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    adventure_id UUID NOT NULL REFERENCES public.adventures(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    client_uuid TEXT,  -- For guest users without auth
    rating TEXT NOT NULL CHECK (rating IN ('positive', 'negative')),
    feedback_text TEXT,  -- Optional text for negative feedback
    contact_info TEXT,   -- Optional contact for guest users with negative feedback
    chapter_number INTEGER NOT NULL DEFAULT 5,
    environment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add comments for documentation
COMMENT ON TABLE public.user_feedback IS 'Stores user feedback collected at chapter 5 of adventures';
COMMENT ON COLUMN public.user_feedback.user_id IS 'Links to authenticated user. NULL for guest users.';
COMMENT ON COLUMN public.user_feedback.client_uuid IS 'UUID for guest users without authentication';
COMMENT ON COLUMN public.user_feedback.rating IS 'Either positive (thumbs up) or negative (thumbs down)';
COMMENT ON COLUMN public.user_feedback.feedback_text IS 'Optional text feedback for negative ratings';
COMMENT ON COLUMN public.user_feedback.contact_info IS 'Optional contact info for guest users';

-- Indexes for common queries
CREATE INDEX idx_user_feedback_user ON public.user_feedback(user_id);
CREATE INDEX idx_user_feedback_client_uuid ON public.user_feedback(client_uuid);
CREATE INDEX idx_user_feedback_rating ON public.user_feedback(rating);
CREATE INDEX idx_user_feedback_created_at ON public.user_feedback(created_at);

-- Enable Row Level Security
ALTER TABLE public.user_feedback ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can insert their own feedback
-- Allows authenticated users (user_id matches) or guest users (user_id is NULL)
CREATE POLICY "Users can insert feedback" ON public.user_feedback
FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

-- RLS Policy: Users can view their own feedback (for future analytics/history features)
CREATE POLICY "Users can view their own feedback" ON public.user_feedback
FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL);
