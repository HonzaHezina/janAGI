-- Migration: 021_chat_schema.sql
-- Description: Adds the basic chat logging table (extracted from 020 update)
-- Apply this if users already have 020 applied but missed the chat update.

CREATE SCHEMA IF NOT EXISTS chat;

CREATE TABLE IF NOT EXISTS chat.messages (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  platform    text NOT NULL DEFAULT 'telegram', -- 'telegram', 'web', 'cli'
  chat_id     text NOT NULL,
  role        text NOT NULL,                 -- 'user', 'assistant', 'system', 'tool'
  content     text NOT NULL,
  metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chat_messages_chat_idx ON chat.messages (platform, chat_id, created_at);
