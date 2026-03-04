-- Add kpi_cards column to chat_messages for storing KPI card JSON (label, value, unit).
-- Run once; if column already exists, ignore the error.
ALTER TABLE chat_messages ADD COLUMN kpi_cards TEXT NULL;
