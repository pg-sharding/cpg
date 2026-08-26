-- Test temp_table_trace module: the ttt.session_owns_temp_rels GUC should
-- reflect whether the current session owns any temporary relations.

-- Initially the module is not loaded; the custom GUC is unknown and reads as
-- an empty/off value.  Load the module to install the hooks.
LOAD 'temp_table_trace';

-- No temp relations yet: GUC should be off.
SHOW ttt.session_owns_temp_rels;

-- Create a temp table.  This is a utility command, so ProcessUtility runs
-- first and invalidates the cached GUC value.  The subsequent ExecutorEnd
-- (from the next query) recomputes it.
CREATE TEMP TABLE z2();

-- Trigger ExecutorEnd so the GUC gets recomputed and reported.
SELECT 1;

-- Now the session owns a temp relation: GUC should be on.
SHOW ttt.session_owns_temp_rels;

-- Drop the temp table (another utility command -> invalidation).
DROP TABLE z2;

-- Trigger ExecutorEnd to recompute.
SELECT 1;

-- No temp relations anymore: GUC should be off again.
SHOW ttt.session_owns_temp_rels;
