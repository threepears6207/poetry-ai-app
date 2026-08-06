PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS poems (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '',
    dynasty TEXT NOT NULL DEFAULT '',
    content_json TEXT NOT NULL DEFAULT '[]',
    translation TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    age_level TEXT NOT NULL DEFAULT '',
    age_range TEXT NOT NULL DEFAULT '',
    difficulty INTEGER NOT NULL DEFAULT 1 CHECK (difficulty >= 1),
    theme_tags_json TEXT NOT NULL DEFAULT '[]',
    knowledge_tags_json TEXT NOT NULL DEFAULT '[]',
    recommend_reason TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL DEFAULT '',
    library_scope TEXT NOT NULL DEFAULT 'core'
        CHECK (library_scope IN ('core', 'extension')),
    source_name TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT '',
    verification_status TEXT NOT NULL DEFAULT 'verified'
        CHECK (verification_status IN ('verified', 'pending', 'rejected')),
    content_complete INTEGER NOT NULL DEFAULT 1 CHECK (content_complete IN (0, 1)),
    recommend_eligible INTEGER NOT NULL DEFAULT 1 CHECK (recommend_eligible IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    age_level TEXT NOT NULL DEFAULT 'age_3_4',
    age_range TEXT NOT NULL DEFAULT '3-4岁',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS poem_aliases (
    alias_id TEXT PRIMARY KEY,
    poem_id TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT 'duplicate_content',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (poem_id) REFERENCES poems(id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS learning_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    poem_id TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL DEFAULT 0 CHECK (duration_seconds >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (poem_id) REFERENCES poems(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS consolidations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    poem_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT '待巩固'
        CHECK (status IN ('待巩固', '已巩固', '已掌握')),
    practice_count INTEGER NOT NULL DEFAULT 0 CHECK (practice_count >= 0),
    next_review_date TEXT NOT NULL DEFAULT '',
    reading_completed INTEGER NOT NULL DEFAULT 0 CHECK (reading_completed IN (0, 1)),
    connection_completed INTEGER NOT NULL DEFAULT 0 CHECK (connection_completed IN (0, 1)),
    collection_state TEXT NOT NULL DEFAULT 'gray'
        CHECK (collection_state IN ('gray', 'color')),
    flower_count INTEGER NOT NULL DEFAULT 0 CHECK (flower_count >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, poem_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (poem_id) REFERENCES poems(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS reading_scores (
    user_id TEXT NOT NULL,
    poem_id TEXT NOT NULL,
    score REAL NOT NULL CHECK (score >= 0 AND score <= 100),
    source TEXT NOT NULL DEFAULT 'reading',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, poem_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (poem_id) REFERENCES poems(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS daily_reminder_settings (
    user_id TEXT NOT NULL,
    setting_date TEXT NOT NULL,
    practice_prompt_suppressed INTEGER NOT NULL DEFAULT 0
        CHECK (practice_prompt_suppressed IN (0, 1)),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, setting_date),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_poems_title ON poems(title);
CREATE INDEX IF NOT EXISTS idx_poems_author ON poems(author);
CREATE INDEX IF NOT EXISTS idx_poems_age_difficulty ON poems(age_level, difficulty);
CREATE INDEX IF NOT EXISTS idx_poems_content_hash ON poems(content_hash);
CREATE INDEX IF NOT EXISTS idx_poems_title_author ON poems(title, author);
CREATE INDEX IF NOT EXISTS idx_poem_aliases_poem ON poem_aliases(poem_id);
CREATE INDEX IF NOT EXISTS idx_learning_records_user_time
    ON learning_records(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_learning_records_user_poem
    ON learning_records(user_id, poem_id);
CREATE INDEX IF NOT EXISTS idx_consolidations_user_review
    ON consolidations(user_id, next_review_date);
CREATE INDEX IF NOT EXISTS idx_reading_scores_user ON reading_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_reminder_user_date
    ON daily_reminder_settings(user_id, setting_date);

INSERT OR IGNORE INTO schema_migrations(version, name)
VALUES (1, 'initial_schema');
