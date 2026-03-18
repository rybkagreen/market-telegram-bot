-- Create user_feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    status feedbackstatus NOT NULL DEFAULT 'new',
    admin_response TEXT,
    responded_at TIMESTAMPTZ,
    responded_by_id INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS ix_user_feedback_status ON user_feedback(status);
