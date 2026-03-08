CREATE SCHEMA IF NOT EXISTS quizplease;

CREATE TABLE IF NOT EXISTS quizplease.telegram_bot_updates (
    bot_name VARCHAR(255) PRIMARY KEY,
    update_id BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'telegram_bot_updates_update_id_check'
    ) THEN
        ALTER TABLE quizplease.telegram_bot_updates
            ADD CONSTRAINT telegram_bot_updates_update_id_check
            CHECK (update_id >= 0);
    END IF;
END
$$;

COMMENT ON TABLE quizplease.telegram_bot_updates IS
    'Stores the last processed Telegram update offset for each bot';
