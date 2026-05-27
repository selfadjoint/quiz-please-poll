CREATE TABLE IF NOT EXISTS quizplease.polls (
    poll_id    TEXT   PRIMARY KEY,
    game_id    INT    NOT NULL,
    message_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE quizplease.polls IS
    'Stores Telegram poll metadata (poll_id, message_id) per game for answer tracking';

CREATE TABLE IF NOT EXISTS quizplease.poll_answers (
    id         BIGSERIAL PRIMARY KEY,
    poll_id    TEXT   NOT NULL REFERENCES quizplease.polls (poll_id),
    user_id    BIGINT NOT NULL,
    username   TEXT,
    first_name TEXT   NOT NULL,
    last_name  TEXT,
    option_ids INT[]  NOT NULL,
    voted_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS poll_answers_poll_user_idx
    ON quizplease.poll_answers (poll_id, user_id, voted_at DESC);

COMMENT ON TABLE quizplease.poll_answers IS
    'Append-only vote event log; empty option_ids = retracted vote';

CREATE OR REPLACE VIEW quizplease.poll_answers_current AS
SELECT DISTINCT ON (poll_id, user_id)
    poll_id, user_id, username, first_name, last_name, option_ids, voted_at
FROM quizplease.poll_answers
ORDER BY poll_id, user_id, voted_at DESC, id DESC;
