-- Add is_sync column to sql_training for tracking Vanna sync status
-- 0 = not synced to Vanna, 1 = synced (used for training)
-- Run once; if column already exists, ignore the error.
ALTER TABLE sql_training ADD COLUMN is_sync INT NOT NULL DEFAULT 0;
