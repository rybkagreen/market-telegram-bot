-- Migration: add telegram_chats and chat_snapshots
-- Create telegram_chats table
CREATE TABLE IF NOT EXISTS telegram_chats (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    telegram_id BIGINT UNIQUE,
    title VARCHAR(512),
    description TEXT,
    chat_type VARCHAR(50) NOT NULL DEFAULT 'channel',
    topic VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    can_post BOOLEAN NOT NULL DEFAULT FALSE,
    last_subscribers INTEGER NOT NULL DEFAULT 0,
    last_avg_views INTEGER NOT NULL DEFAULT 0,
    last_er FLOAT NOT NULL DEFAULT 0.0,
    last_post_frequency FLOAT NOT NULL DEFAULT 0.0,
    last_parsed_at TIMESTAMP,
    parse_error TEXT,
    parse_error_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create chat_snapshots table
CREATE TABLE IF NOT EXISTS chat_snapshots (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES telegram_chats(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    subscribers INTEGER NOT NULL DEFAULT 0,
    subscribers_delta INTEGER NOT NULL DEFAULT 0,
    subscribers_delta_pct FLOAT NOT NULL DEFAULT 0.0,
    avg_views INTEGER NOT NULL DEFAULT 0,
    max_views INTEGER NOT NULL DEFAULT 0,
    min_views INTEGER NOT NULL DEFAULT 0,
    posts_analyzed INTEGER NOT NULL DEFAULT 0,
    er FLOAT NOT NULL DEFAULT 0.0,
    post_frequency FLOAT NOT NULL DEFAULT 0.0,
    posts_last_30d INTEGER NOT NULL DEFAULT 0,
    can_post BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (chat_id, snapshot_date)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_telegram_chats_username ON telegram_chats(username);
CREATE INDEX IF NOT EXISTS ix_telegram_chats_telegram_id ON telegram_chats(telegram_id);
CREATE INDEX IF NOT EXISTS ix_telegram_chats_is_active ON telegram_chats(is_active);
CREATE INDEX IF NOT EXISTS ix_chat_snapshots_chat_id ON chat_snapshots(chat_id);
CREATE INDEX IF NOT EXISTS ix_chat_snapshots_snapshot_date ON chat_snapshots(snapshot_date);
