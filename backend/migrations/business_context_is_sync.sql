-- Add is_sync column to business_context for tracking Vanna sync status
-- 0 = not synced to Vanna, 1 = synced (used for training)
-- Run once; if column already exists, ignore the error.
ALTER TABLE business_context ADD COLUMN is_sync INT NOT NULL DEFAULT 0;
