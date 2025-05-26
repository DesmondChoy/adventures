-- Link adventures.user_id to auth.users
ALTER TABLE public.adventures
ADD CONSTRAINT fk_adventures_auth_users FOREIGN KEY (user_id)
REFERENCES auth.users (id) ON DELETE SET NULL;

COMMENT ON COLUMN public.adventures.user_id IS 'Links to the authenticated user in auth.users table. SET NULL on user deletion.';

-- Link telemetry_events.user_id to auth.users
ALTER TABLE public.telemetry_events
ADD CONSTRAINT fk_telemetry_events_auth_users FOREIGN KEY (user_id)
REFERENCES auth.users (id) ON DELETE SET NULL;

COMMENT ON COLUMN public.telemetry_events.user_id IS 'Links to the authenticated user in auth.users table. SET NULL on user deletion.';

-- Ensure RLS is enabled on telemetry_events (already enabled on adventures as per wip/supabase_integration.md Phase 2.1)
ALTER TABLE public.telemetry_events ENABLE ROW LEVEL SECURITY;

-- RLS Policies for 'adventures' table
-- Drop old service key policy if it was too broad and only allowed service key.
-- Example: DROP POLICY IF EXISTS "Allow backend access via service key" ON public.adventures;
-- Supabase's service_role bypasses RLS by default, so an explicit "allow all for service_role" policy is often redundant.

-- Policies for users interacting via frontend (anon key / authenticated user JWT)
CREATE POLICY "Users can select their own or guest adventures" ON public.adventures
FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL); -- Allow selection if user matches or if adventure is a guest adventure (user_id is NULL)

CREATE POLICY "Users can insert adventures for themselves or as guest" ON public.adventures
FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL); -- Allow insert if user matches or if inserting as guest (user_id will be NULL initially for guest)

CREATE POLICY "Users can update their own adventures" ON public.adventures
FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id); -- Only allow updating their own, identified by user_id matching auth.uid()

-- Deletion of adventures might be restricted or handled differently (e.g., soft delete or admin only).
-- For now, not adding a user delete policy. Service role can still delete.
-- CREATE POLICY "Users can delete their own adventures" ON public.adventures
-- FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for 'telemetry_events' table
-- Service_role bypasses RLS by default.

CREATE POLICY "Users can insert their own telemetry" ON public.telemetry_events
FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL); -- Allow insert if user matches or if telemetry is for a guest session

-- Select/update/delete on telemetry_events are typically more restricted.
-- Users might only be allowed to see their own telemetry if a dashboard feature was built.
-- For now, focusing on insert.
-- CREATE POLICY "Users can select their own telemetry" ON public.telemetry_events
-- FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL);
