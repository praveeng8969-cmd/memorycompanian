"""Run from the project root: python -m Backend.app or python run.py.

Supervised cognitive engagement and memory assistance prototype for demonstration.
"""
import json, os, sqlite3, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from functools import partial

from Backend.policy import recommend, LEVEL_CONFIG, get_level_config

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get('MEMORY_DB', ROOT / 'Backend' / 'memory.db'))
MODEL = None
MODEL_ERROR = None

def connect():
    con = sqlite3.connect(DB, timeout=15.0)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con

def migrate(con):
    """Safely apply non-destructive schema migrations preserving existing records."""
    # Check profile columns
    cols_profile = [r['name'] for r in con.execute("PRAGMA table_info(profile)").fetchall()]
    if 'auto_apply_plan' not in cols_profile:
        con.execute("ALTER TABLE profile ADD COLUMN auto_apply_plan INTEGER NOT NULL DEFAULT 0 CHECK(auto_apply_plan IN (0,1))")

    # Check reminders columns
    cols_reminders = [r['name'] for r in con.execute("PRAGMA table_info(reminders)").fetchall()]
    if 'acknowledged_at' not in cols_reminders:
        con.execute("ALTER TABLE reminders ADD COLUMN acknowledged_at TEXT")

    # Check memories columns
    cols_memories = [r['name'] for r in con.execute("PRAGMA table_info(memories)").fetchall()]
    if 'created_at' not in cols_memories:
        con.execute("ALTER TABLE memories ADD COLUMN created_at TEXT NOT NULL DEFAULT ''")
    if 'updated_at' not in cols_memories:
        con.execute("ALTER TABLE memories ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")

    # Check sessions columns
    cols_sessions = [r['name'] for r in con.execute("PRAGMA table_info(sessions)").fetchall()]
    if 'client_session_id' not in cols_sessions:
        con.execute("ALTER TABLE sessions ADD COLUMN client_session_id TEXT")
    if 'activity' not in cols_sessions:
        con.execute("ALTER TABLE sessions ADD COLUMN activity TEXT NOT NULL DEFAULT 'matching'")
    if 'policy_version' not in cols_sessions:
        con.execute("ALTER TABLE sessions ADD COLUMN policy_version TEXT NOT NULL DEFAULT 'report_exact_2.0'")
    if 'status' not in cols_sessions:
        con.execute("ALTER TABLE sessions ADD COLUMN status TEXT NOT NULL DEFAULT 'completed'")
    if 'boards_completed' not in cols_sessions:
        con.execute("ALTER TABLE sessions ADD COLUMN boards_completed INTEGER NOT NULL DEFAULT 1")
    if 'total_boards' not in cols_sessions:
        con.execute("ALTER TABLE sessions ADD COLUMN total_boards INTEGER NOT NULL DEFAULT 1")
    if 'reason' not in cols_sessions:
        con.execute("ALTER TABLE sessions ADD COLUMN reason TEXT")
    if 'caregiver_reason' not in cols_sessions:
        con.execute("ALTER TABLE sessions ADD COLUMN caregiver_reason TEXT")

    # Ensure next_plan table exists
    con.execute("""
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
    """)
    con.execute("""
    INSERT OR IGNORE INTO next_plan(id, target_level, pairs_per_board, total_boards, activity_name, reason, caregiver_reason, status, approved_at)
    VALUES(1, 1, 3, 2, 'Familiar Pair Matching', 'Welcome! Enjoy a comfortable activity with familiar objects.', 'Initial baseline configuration.', 'approved', CURRENT_TIMESTAMP);
    """)

def seed_sample_memories(con):
    """Seed gentle, familiar cultural demo examples if memories table is completely empty."""
    count = con.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    if count == 0:
        samples = [
            ("Family Tea Time", "Remembering our gentle morning tea together on the front porch with warm chai.", 1),
            ("Lush Green Hills", "The morning mist rising softly over the quiet tea gardens and bamboo groves.", 1),
            ("Garden Marigolds", "Bright orange and yellow flowers blooming by the courtyard gate.", 1),
        ]
        con.executemany("INSERT INTO memories(title, description, approved) VALUES(?,?,?)", samples)

def initialize():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        con.executescript((ROOT / 'Backend/schema.sql').read_text(encoding='utf-8'))
        migrate(con)
        seed_sample_memories(con)

def load_model():
    global MODEL, MODEL_ERROR
    try:
        import joblib
        model_path = ROOT / 'ML/artifacts/model.joblib'
        if model_path.exists():
            MODEL = joblib.load(model_path)
            MODEL_ERROR = None
        else:
            MODEL = None
            MODEL_ERROR = 'ModelFileNotFound'
    except Exception as exc:
        MODEL = None
        MODEL_ERROR = type(exc).__name__
        print('ML unavailable; transparent rule policy remains active:', MODEL_ERROR)

def bounded_int(data, key, lo, hi):
    v = data.get(key)
    if type(v) is not int or not lo <= v <= hi:
        raise ValueError(f'{key} must be an integer from {lo} to {hi}')
    return v

def clean_text(data, key, limit):
    v = data.get(key)
    if not isinstance(v, str) or not v.strip() or len(v.strip()) > limit:
        raise ValueError(f'{key} must contain 1-{limit} characters')
    return v.strip()

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def reply(self, status, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/health':
            return self.reply(200, {
                'ok': True,
                'model_loaded': MODEL is not None,
                'model_error': MODEL_ERROR,
                'policy_version': 'report_exact_2.0',
                'min_attempts_required': 5,
            })

        if path == '/api/plan':
            with connect() as c:
                plan = dict(c.execute('SELECT * FROM next_plan WHERE id=1').fetchone())
            return self.reply(200, {'plan': plan, 'level_config': LEVEL_CONFIG.get(plan['target_level'])})

        if path == '/api/dashboard':
            with connect() as c:
                profile = dict(c.execute('SELECT * FROM profile WHERE id=1').fetchone())
                plan = dict(c.execute('SELECT * FROM next_plan WHERE id=1').fetchone())
                memories = [dict(r) for r in c.execute('SELECT * FROM memories ORDER BY id DESC')]
                reminders = [dict(r) for r in c.execute('SELECT * FROM reminders ORDER BY id DESC')]
                sessions = [dict(r) for r in c.execute('SELECT * FROM sessions ORDER BY id DESC LIMIT 100')]
            return self.reply(200, {
                'profile': profile,
                'next_plan': plan,
                'memories': memories,
                'reminders': reminders,
                'sessions': sessions,
                'model_loaded': MODEL is not None,
                'level_configs': LEVEL_CONFIG,
            })

        if path.startswith('/api/'):
            return self.reply(404, {'error': 'Unknown endpoint'})

        if path not in ['/', '/index.html', '/style.css', '/app.js']:
            return self.reply(404, {'error': 'Not found'})

        super().do_GET()

    def do_POST(self):
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            return self.reply(403, {'error': 'Cross-origin writes are disabled'})

        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 0 or length > 32768:
                raise ValueError('Request payload too large')
            raw = self.rfile.read(length) if length > 0 else b'{}'
            data = json.loads(raw or b'{}')
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object')

            path = urlparse(self.path).path
            with connect() as c:
                # 1. Update Profile
                if path == '/api/profile':
                    name = clean_text(data, 'name', 80)
                    if type(data.get('consent')) is not bool:
                        raise ValueError('consent must be boolean')
                    auto_apply = data.get('auto_apply_plan', False)
                    if type(auto_apply) is not bool:
                        raise ValueError('auto_apply_plan must be boolean')
                    c.execute(
                        'UPDATE profile SET name=?, consent=?, auto_apply_plan=? WHERE id=1',
                        (name, int(data['consent']), int(auto_apply))
                    )
                    c.commit()
                    return self.reply(200, {'saved': True})

                # 2. Approve Next Activity Plan
                if path == '/api/plan/approve':
                    row = c.execute('SELECT * FROM next_plan WHERE id=1').fetchone()
                    if not row:
                        return self.reply(404, {'error': 'Plan not found'})
                    now = datetime.now(timezone.utc).isoformat()
                    c.execute("UPDATE next_plan SET status='approved', approved_at=?, updated_at=CURRENT_TIMESTAMP WHERE id=1", (now,))
                    c.commit()
                    updated = dict(c.execute('SELECT * FROM next_plan WHERE id=1').fetchone())
                    return self.reply(200, {'saved': True, 'plan': updated})

                # 3. Override Next Activity Plan
                if path == '/api/plan/override':
                    level = bounded_int(data, 'level', 1, 3)
                    override_reason = clean_text(data, 'reason', 300)
                    cfg = get_level_config(level)
                    now = datetime.now(timezone.utc).isoformat()
                    c.execute("""
                        UPDATE next_plan
                        SET target_level=?, pairs_per_board=?, total_boards=?,
                            caregiver_reason=?, status='overridden',
                            override_reason=?, approved_at=?, updated_at=CURRENT_TIMESTAMP
                        WHERE id=1
                    """, (level, cfg['pairs_per_board'], cfg['total_boards'],
                          f"Caregiver override to Level {level} ({cfg['name']}).",
                          override_reason, now))
                    c.commit()
                    updated = dict(c.execute('SELECT * FROM next_plan WHERE id=1').fetchone())
                    return self.reply(200, {'saved': True, 'plan': updated})

                # 4. Save Session (with Idempotency Key & Atomic Plan Update)
                if path == '/api/sessions':
                    profile = dict(c.execute('SELECT consent, auto_apply_plan FROM profile WHERE id=1').fetchone())
                    if not profile['consent']:
                        return self.reply(403, {'error': 'Caregiver consent is required to save activity measures'})

                    client_id = data.get('client_session_id')
                    if client_id is not None:
                        if not isinstance(client_id, str) or len(client_id) > 64:
                            raise ValueError('Invalid client_session_id')
                        # Check idempotency
                        existing = c.execute('SELECT * FROM sessions WHERE client_session_id=?', (client_id,)).fetchone()
                        if existing:
                            plan = dict(c.execute('SELECT * FROM next_plan WHERE id=1').fetchone())
                            return self.reply(200, {
                                'saved': True,
                                'idempotent': True,
                                'session': dict(existing),
                                'plan': plan,
                                'recommendation': existing['recommendation'],
                                'next_level': existing['next_level'],
                                'reason': existing['reason'],
                                'caregiver_reason': existing['caregiver_reason'],
                                'model_action': existing['model_action'],
                            })
                    else:
                        client_id = str(uuid.uuid4())

                    correct = bounded_int(data, 'correct', 0, 10000)
                    attempts = bounded_int(data, 'attempts', 0, 10000)
                    hints = bounded_int(data, 'hints', 0, 10000)
                    level = bounded_int(data, 'level', 1, 3)
                    if correct > attempts:
                        raise ValueError('correct cannot exceed attempts')

                    paused = data.get('paused')
                    if type(paused) is not bool:
                        raise ValueError('paused must be boolean')

                    boards_completed = bounded_int(data, 'boards_completed', 1, 10) if 'boards_completed' in data else 1
                    total_boards = bounded_int(data, 'total_boards', 1, 10) if 'total_boards' in data else 1
                    status_str = 'paused' if paused else ('completed' if boards_completed >= total_boards else 'partial')

                    action, next_level, reason, caregiver_reason, next_cfg = recommend(correct, attempts, hints, level, paused)

                    # ML Model Inference (only eligible with at least 5 genuine attempts)
                    model_action = None
                    if MODEL is not None and attempts >= 5:
                        try:
                            import pandas as pd
                            row = {
                                'activity': 'matching',
                                'level': level,
                                'accuracy': correct / attempts,
                                'hint_rate': min(hints / attempts, 1.0),
                                'paused': int(paused)
                            }
                            model_action = str(MODEL.predict(pd.DataFrame([row]))[0])
                        except Exception as m_err:
                            print('Model inference error:', repr(m_err), file=sys.stderr)
                            model_action = None

                    # Insert Session
                    cur = c.execute("""
                        INSERT INTO sessions(
                            client_session_id, activity, policy_version, status,
                            correct, attempts, hints, paused, level,
                            boards_completed, total_boards,
                            recommendation, next_level, reason, caregiver_reason, model_action
                        ) VALUES(?, 'matching', 'report_exact_2.0', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (client_id, status_str, correct, attempts, hints, int(paused), level,
                          boards_completed, total_boards, action, next_level, reason, caregiver_reason, model_action))
                    session_id = cur.lastrowid

                    # Determine Plan Approval State
                    now = datetime.now(timezone.utc).isoformat()
                    if profile['auto_apply_plan'] and action in ('advance', 'simplify', 'maintain'):
                        plan_status = 'approved'
                        approved_at = now
                    elif action == 'insufficient_evidence':
                        plan_status = 'approved'
                        approved_at = now
                    else:
                        plan_status = 'pending'
                        approved_at = None

                    # Atomically update next_plan
                    c.execute("""
                        UPDATE next_plan
                        SET target_level=?, pairs_per_board=?, total_boards=?,
                            activity_name='Familiar Pair Matching',
                            reason=?, caregiver_reason=?, status=?,
                            source_session_id=?, approved_at=?, override_reason=NULL,
                            updated_at=CURRENT_TIMESTAMP
                        WHERE id=1
                    """, (next_level, next_cfg['pairs_per_board'], next_cfg['total_boards'],
                          reason, caregiver_reason, plan_status, session_id, approved_at))

                    c.commit()

                    saved_session = dict(c.execute('SELECT * FROM sessions WHERE id=?', (session_id,)).fetchone())
                    saved_plan = dict(c.execute('SELECT * FROM next_plan WHERE id=1').fetchone())

                    return self.reply(201, {
                        'saved': True,
                        'session': saved_session,
                        'plan': saved_plan,
                        'recommendation': action,
                        'next_level': next_level,
                        'reason': reason,
                        'caregiver_reason': caregiver_reason,
                        'model_action': model_action,
                        'review_required': (plan_status == 'pending'),
                    })

                # 5. Memories Endpoints
                if path == '/api/memories':
                    title = clean_text(data, 'title', 100)
                    description = clean_text(data, 'description', 1000)
                    if type(data.get('approved')) is not bool:
                        raise ValueError('approved must be boolean')
                    cur = c.execute('INSERT INTO memories(title, description, approved) VALUES(?,?,?)',
                                    (title, description, int(data['approved'])))
                    c.commit()
                    return self.reply(201, {'saved': True, 'id': cur.lastrowid})

                # Memories Update / Delete
                parts = path.strip('/').split('/')
                if len(parts) == 4 and parts[:2] == ['api', 'memories']:
                    mem_id = int(parts[2])
                    if parts[3] == 'update':
                        title = clean_text(data, 'title', 100)
                        description = clean_text(data, 'description', 1000)
                        if type(data.get('approved')) is not bool:
                            raise ValueError('approved must be boolean')
                        cur = c.execute(
                            'UPDATE memories SET title=?, description=?, approved=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
                            (title, description, int(data['approved']), mem_id)
                        )
                        c.commit()
                        return self.reply(200 if cur.rowcount else 404, {'saved': bool(cur.rowcount)})
                    if parts[3] == 'delete':
                        cur = c.execute('DELETE FROM memories WHERE id=?', (mem_id,))
                        c.commit()
                        return self.reply(200 if cur.rowcount else 404, {'deleted': bool(cur.rowcount)})

                # 6. Reminders Endpoints
                if path == '/api/reminders':
                    title = clean_text(data, 'title', 120)
                    due = clean_text(data, 'due_at', 40)
                    datetime.fromisoformat(due)
                    cur = c.execute('INSERT INTO reminders(title, due_at) VALUES(?,?)', (title, due))
                    c.commit()
                    return self.reply(201, {'saved': True, 'id': cur.lastrowid})

                # Reminders Acknowledge / Update / Delete
                if len(parts) == 4 and parts[:2] == ['api', 'reminders']:
                    rem_id = int(parts[2])
                    if parts[3] == 'acknowledge':
                        now = datetime.now(timezone.utc).isoformat()
                        cur = c.execute('UPDATE reminders SET acknowledged=1, acknowledged_at=? WHERE id=?', (now, rem_id))
                        c.commit()
                        return self.reply(200 if cur.rowcount else 404, {'saved': bool(cur.rowcount)})
                    if parts[3] == 'update':
                        title = clean_text(data, 'title', 120)
                        due = clean_text(data, 'due_at', 40)
                        datetime.fromisoformat(due)
                        cur = c.execute('UPDATE reminders SET title=?, due_at=? WHERE id=?', (title, due, rem_id))
                        c.commit()
                        return self.reply(200 if cur.rowcount else 404, {'saved': bool(cur.rowcount)})
                    if parts[3] == 'delete':
                        cur = c.execute('DELETE FROM reminders WHERE id=?', (rem_id,))
                        c.commit()
                        return self.reply(200 if cur.rowcount else 404, {'deleted': bool(cur.rowcount)})

                return self.reply(404, {'error': 'Unknown endpoint'})
        except (ValueError, TypeError, KeyError) as exc:
            self.reply(400, {'error': str(exc)})
        except Exception as exc:
            print('Server error:', repr(exc), file=sys.stderr)
            self.reply(500, {'error': 'Server could not complete the request'})

def main():
    initialize()
    load_model()
    port = int(os.environ.get('PORT', '8000'))
    candidates = [port] if 'PORT' in os.environ else [8000, 8001, 8002, 8080]
    server = None
    for p in candidates:
        try:
            server = ThreadingHTTPServer(('127.0.0.1', p), partial(Handler, directory=str(ROOT / 'Frontend')))
            port = p
            break
        except OSError:
            if 'PORT' in os.environ:
                raise
    if server is None:
        raise OSError(f'Could not bind server to ports: {candidates}')
    print(f'Memory Companion: http://127.0.0.1:{port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
