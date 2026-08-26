CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  name TEXT NOT NULL,
  value REAL NOT NULL,
  tags_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_metrics_name_ts ON metrics(name, ts);

CREATE TABLE IF NOT EXISTS session_index (
  session_id TEXT PRIMARY KEY,
  symbol TEXT,
  topic TEXT,
  updated_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS instrument_memory (
  symbol TEXT PRIMARY KEY,
  name TEXT DEFAULT '',
  sector TEXT DEFAULT '',
  conclusions_json TEXT NOT NULL DEFAULT '[]',
  price_anchors_json TEXT NOT NULL DEFAULT '[]',
  hit_total INTEGER NOT NULL DEFAULT 0,
  hit_ok INTEGER NOT NULL DEFAULT 0,
  updated_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS semantic_memory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '',
  source_trace TEXT DEFAULT '',
  created_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE VIRTUAL TABLE IF NOT EXISTS semantic_fts USING fts5(content, tags, content='semantic_memory', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS semantic_ai AFTER INSERT ON semantic_memory BEGIN
  INSERT INTO semantic_fts(rowid,content,tags) VALUES (new.id,new.content,new.tags);
END;
CREATE TABLE IF NOT EXISTS user_profile (
  user_id TEXT PRIMARY KEY DEFAULT 'default',
  risk_preference TEXT DEFAULT '',
  style TEXT DEFAULT '',
  watchlist_json TEXT NOT NULL DEFAULT '[]',
  feedback_json TEXT NOT NULL DEFAULT '[]',
  updated_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS predictions (
  prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
  trace_id TEXT,
  symbol TEXT NOT NULL,
  made_at REAL NOT NULL,
  direction TEXT NOT NULL,
  confidence REAL NOT NULL,
  target_low REAL,
  target_high REAL,
  horizon_days INTEGER NOT NULL,
  invalidation_json TEXT NOT NULL DEFAULT '[]',
  rationale TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending',
  verdict TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS user_goals (
  goal_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL DEFAULT 'default',
  title TEXT NOT NULL,
  symbol TEXT,
  cadence_days INTEGER NOT NULL DEFAULT 30,
  last_run_at REAL,
  next_run_at REAL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at REAL NOT NULL DEFAULT (strftime('%s','now')),
  notes TEXT DEFAULT ''
);
