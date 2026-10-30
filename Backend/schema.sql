PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK(id=1),
    name TEXT NOT NULL,
    consent INTEGER NOT NULL DEFAULT 0 CHECK(consent IN (0,1)),
    auto_apply_plan INTEGER NOT NULL DEFAULT 0 CHECK(auto_apply_plan IN (0,1))
);
INSERT OR IGNORE INTO profile(id, name, consent) VALUES(1, 'Demo participant', 0);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    client_session_id TEXT UNIQUE,
    activity TEXT NOT NULL DEFAULT 'matching',
    policy_version TEXT NOT NULL DEFAULT 'report_exact_2.0',
    status TEXT NOT NULL DEFAULT 'completed',
    correct INTEGER NOT NULL,
    attempts INTEGER NOT NULL,
    hints INTEGER NOT NULL,
    paused INTEGER NOT NULL,
    level INTEGER NOT NULL,
    boards_completed INTEGER NOT NULL DEFAULT 1,
    total_boards INTEGER NOT NULL DEFAULT 1,
    recommendation TEXT NOT NULL,
    next_level INTEGER NOT NULL,
    reason TEXT,
    caregiver_reason TEXT,
    model_action TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS next_plan (
    id INTEGER PRIMARY KEY CHECK(id=1),
    target_level INTEGER NOT NULL DEFAULT 1 CHECK(target_level BETWEEN 1 AND 3),
    pairs_per_board INTEGER NOT NULL DEFAULT 3,
    total_boards INTEGER NOT NULL DEFAULT 2,
    activity_name TEXT NOT NULL DEFAULT 'Familiar Pair Matching',
    reason TEXT NOT NULL DEFAULT 'Welcome! Start whenever you are ready.',
    caregiver_reason TEXT NOT NULL DEFAULT 'Initial activity baseline.',
    status TEXT NOT NULL DEFAULT 'approved' CHECK(status IN ('pending', 'approved', 'overridden')),
    source_session_id INTEGER,
    approved_at TEXT,
    override_reason TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_session_id) REFERENCES sessions(id)
);
INSERT OR IGNORE INTO next_plan(id, target_level, pairs_per_board, total_boards, activity_name, reason, caregiver_reason, status, approved_at)
VALUES(1, 1, 3, 2, 'Familiar Pair Matching', 'Welcome! Enjoy a comfortable activity with familiar objects.', 'Initial baseline configuration.', 'approved', CURRENT_TIMESTAMP);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    approved INTEGER NOT NULL CHECK(approved IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    due_at TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0 CHECK(acknowledged IN (0,1)),
    acknowledged_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
