"""Comprehensive unit and integration test suite for Memory Companion.

Verifies report policy rules, multi-board adaptation, database migration,
session idempotency, caregiver supervision/override, and ML pipeline isolation.
"""
import json, os, sqlite3, subprocess, sys, tempfile, time, unittest, uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Backend.policy import recommend, action, LEVEL_CONFIG

class PolicyTests(unittest.TestCase):
    def test_report_ordered_rules_and_boundaries(self):
        """Verify report policy boundaries and conditions."""
        cases = [
            # 9 correct / 10 attempts / 1 hint at level 1 -> advance to level 2
            ((9, 10, 1, 1, False), ('advance', 2)),
            # 3 / 10 / 6 at level 2 -> simplify to level 1
            ((3, 10, 6, 2, False), ('simplify', 1)),
            # 7 / 10 / 3 at level 2 -> maintain level 2
            ((7, 10, 3, 2, False), ('maintain', 2)),
            # 17 / 20 / 4 -> advance at the exact 85% and 20% boundaries
            ((17, 20, 4, 1, False), ('advance', 2)),
            # 5 / 10 / 5 -> maintain at the exact 50% boundaries
            ((5, 10, 5, 2, False), ('maintain', 2)),
            # 5 / 10 / 6 -> simplify (hint_rate 0.60 > 0.50)
            ((5, 10, 6, 2, False), ('simplify', 1)),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                res = recommend(*args)
                self.assertEqual((res[0], res[1]), expected)

    def test_insufficient_evidence_threshold(self):
        """Verify that fewer than 5 attempts always result in insufficient_evidence."""
        # 4 / 4 / 0 -> insufficient_evidence
        res4 = recommend(4, 4, 0, 1, False)
        self.assertEqual(res4[0], 'insufficient_evidence')
        self.assertEqual(res4[1], 1)

        # Early finish after first 3-pair board (3 attempts) -> insufficient_evidence
        res3 = recommend(3, 3, 0, 1, False)
        self.assertEqual(res3[0], 'insufficient_evidence')
        self.assertEqual(res3[1], 1)

        # Zero attempts session safeguard
        res0 = recommend(0, 0, 0, 2, False)
        self.assertEqual(res0[0], 'insufficient_evidence')
        self.assertEqual(res0[1], 2)

    def test_level_limits_and_clamping(self):
        """Level limits must stay within 1..3 and clearly explain ceiling/floor."""
        # At level 3, advance stays at level 3
        res_ceil = recommend(10, 10, 0, 3, False)
        self.assertEqual(res_ceil[0], 'advance')
        self.assertEqual(res_ceil[1], 3)
        self.assertIn("maximum level 3", res_ceil[3])

        # At level 1, simplification stays at level 1
        res_floor = recommend(0, 10, 0, 1, False)
        self.assertEqual(res_floor[0], 'simplify')
        self.assertEqual(res_floor[1], 1)
        self.assertIn("minimum level 1", res_floor[3])

    def test_pause_precedence(self):
        """Any paused session must return pause and retain current level."""
        res_pause_high = recommend(10, 10, 0, 1, True)
        self.assertEqual(res_pause_high[0], 'pause')
        self.assertEqual(res_pause_high[1], 1)

        res_pause_low = recommend(1, 2, 0, 2, True)
        self.assertEqual(res_pause_low[0], 'pause')
        self.assertEqual(res_pause_low[1], 2)

    def test_multi_board_genuine_attempts(self):
        """A perfect level-1 activity across two boards gives 6 genuine attempts and can advance."""
        # Level 1 has 3 pairs * 2 boards = 6 pairs. Perfect play yields 6 correct out of 6 attempts.
        res = recommend(6, 6, 0, 1, False)
        self.assertEqual(res[0], 'advance')
        self.assertEqual(res[1], 2)

class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / 'test.db'
        cls.base = 'http://127.0.0.1:18082'
        cls.proc = subprocess.Popen(
            [sys.executable, '-m', 'Backend.app'],
            cwd=str(PROJECT_ROOT),
            env={**os.environ, 'MEMORY_DB': str(cls.db_path), 'PORT': '18082'},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        for _ in range(100):
            try:
                cls.call('/api/health')
                return
            except OSError:
                time.sleep(0.1)
        cls.proc.terminate()
        cls.proc.wait()
        cls.tmp.cleanup()
        raise RuntimeError('Test server did not start')

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except Exception:
            cls.proc.kill()
        time.sleep(0.3)
        try:
            cls.tmp.cleanup()
        except Exception:
            pass

    def setUp(self):
        # Reset profile to clean supervised default
        self.call('/api/profile', dict(name='Demo participant', consent=False, auto_apply_plan=False))

    @classmethod
    def call(cls, path, payload=None, headers=None):
        req_headers = {'Content-Type': 'application/json'}
        if headers:
            req_headers.update(headers)
        data = None if payload is None else json.dumps(payload).encode('utf-8')
        req = Request(cls.base + path, data=data, headers=req_headers)
        with urlopen(req, timeout=10) as response:
            return json.load(response)

    def test_health_and_endpoints(self):
        health = self.call('/api/health')
        self.assertTrue(health.get('ok'))
        self.assertEqual(health.get('policy_version'), 'report_exact_2.0')
        self.assertEqual(health.get('min_attempts_required'), 5)

    def test_consent_denial_and_revocation(self):
        payload = dict(
            client_session_id=str(uuid.uuid4()),
            correct=6, attempts=6, hints=0, level=1, paused=False
        )
        # 1. Denied when consent is False
        with self.assertRaises(HTTPError) as ctx:
            self.call('/api/sessions', payload)
        self.assertEqual(ctx.exception.code, 403)

        # 2. Permitted when consent is granted
        self.call('/api/profile', dict(name='Alice', consent=True))
        res = self.call('/api/sessions', payload)
        self.assertEqual(res['recommendation'], 'advance')

        # 3. Denied when consent is revoked
        self.call('/api/profile', dict(name='Alice', consent=False))
        payload['client_session_id'] = str(uuid.uuid4())
        with self.assertRaises(HTTPError) as ctx:
            self.call('/api/sessions', payload)
        self.assertEqual(ctx.exception.code, 403)

    def test_idempotency_duplicate_save(self):
        self.call('/api/profile', dict(name='Bob', consent=True))
        client_id = 'sess-idemp-' + str(uuid.uuid4())
        payload = dict(
            client_session_id=client_id,
            correct=6, attempts=6, hints=0, level=1, paused=False
        )

        res1 = self.call('/api/sessions', payload)
        self.assertTrue(res1['saved'])
        self.assertEqual(res1['recommendation'], 'advance')

        # Retry same save with same client_session_id
        res2 = self.call('/api/sessions', payload)
        self.assertTrue(res2['saved'])
        self.assertTrue(res2.get('idempotent'))

        # Confirm only one session recorded
        dash = self.call('/api/dashboard')
        matching_sessions = [s for s in dash['sessions'] if s.get('client_session_id') == client_id]
        self.assertEqual(len(matching_sessions), 1)

    def test_plan_persistence_and_approval_flow(self):
        """Verify that recommendations generate durable plans requiring caregiver approval by default."""
        self.call('/api/profile', dict(name='Charlie', consent=True, auto_apply_plan=False))

        # Two-board completed session at Level 1 advancing to Level 2
        payload = dict(
            client_session_id=str(uuid.uuid4()),
            correct=6, attempts=6, hints=0, level=1, paused=False,
            boards_completed=2, total_boards=2
        )
        res = self.call('/api/sessions', payload)
        self.assertEqual(res['recommendation'], 'advance')
        self.assertEqual(res['next_level'], 2)
        self.assertTrue(res['review_required'])

        # Verify plan is durably stored in SQLite as pending
        plan_res = self.call('/api/plan')
        self.assertEqual(plan_res['plan']['target_level'], 2)
        self.assertEqual(plan_res['plan']['status'], 'pending')

        # Caregiver approves plan
        appr = self.call('/api/plan/approve', {})
        self.assertTrue(appr['saved'])
        self.assertEqual(appr['plan']['status'], 'approved')

        # Refresh / fetch confirms approved state and configuration
        plan_updated = self.call('/api/plan')
        self.assertEqual(plan_updated['plan']['status'], 'approved')
        self.assertEqual(plan_updated['plan']['target_level'], 2)
        self.assertEqual(plan_updated['plan']['pairs_per_board'], 4)
        self.assertEqual(plan_updated['plan']['total_boards'], 2)

    def test_caregiver_override(self):
        self.call('/api/profile', dict(name='David', consent=True))
        override_payload = dict(level=3, reason="Participant requested a challenge today")
        res = self.call('/api/plan/override', override_payload)
        self.assertTrue(res['saved'])
        self.assertEqual(res['plan']['target_level'], 3)
        self.assertEqual(res['plan']['status'], 'overridden')
        self.assertEqual(res['plan']['pairs_per_board'], 5)
        self.assertEqual(res['plan']['total_boards'], 1)

    def test_auto_apply_setting_safeguards(self):
        # Enable auto-apply in demo setting
        self.call('/api/profile', dict(name='Eva', consent=True, auto_apply_plan=True))

        # Eligible advance recommendation is auto-approved
        sess1 = self.call('/api/sessions', dict(
            client_session_id=str(uuid.uuid4()),
            correct=6, attempts=6, hints=0, level=1, paused=False
        ))
        self.assertEqual(sess1['plan']['status'], 'approved')

        # Paused session is NEVER auto-approved
        sess2 = self.call('/api/sessions', dict(
            client_session_id=str(uuid.uuid4()),
            correct=2, attempts=2, hints=0, level=2, paused=True
        ))
        self.assertEqual(sess2['recommendation'], 'pause')
        self.assertEqual(sess2['plan']['status'], 'pending')

    def test_memories_and_reminders_crud(self):
        self.call('/api/profile', dict(name='Frank', consent=True))

        # Memories CRUD
        mem_create = self.call('/api/memories', dict(title='River Picnic', description='Quiet river bank', approved=True))
        mem_id = mem_create['id']
        self.call(f'/api/memories/{mem_id}/update', dict(title='River Picnic Updated', description='Warm sun', approved=False))
        dash1 = self.call('/api/dashboard')
        self.assertEqual(dash1['memories'][0]['approved'], 0)
        self.call(f'/api/memories/{mem_id}/delete', {})

        # Reminders CRUD & Acknowledgement
        rem_create = self.call('/api/reminders', dict(title='Morning walk', due_at='2026-10-31T09:00'))
        rem_id = rem_create['id']
        self.call(f'/api/reminders/{rem_id}/acknowledge', {})
        dash2 = self.call('/api/dashboard')
        self.assertEqual(dash2['reminders'][0]['acknowledged'], 1)
        self.assertIsNotNone(dash2['reminders'][0].get('acknowledged_at'))
        self.call(f'/api/reminders/{rem_id}/update', dict(title='Evening walk', due_at='2026-10-31T17:00'))
        self.call(f'/api/reminders/{rem_id}/delete', {})

    def test_non_destructive_migration(self):
        """Verify that older databases missing new columns survive migration cleanly."""
        legacy_db = Path(tempfile.gettempdir()) / f"legacy_{uuid.uuid4().hex}.db"
        try:
            with sqlite3.connect(legacy_db) as con:
                # Create old-style schema without new columns
                con.execute("CREATE TABLE profile(id INTEGER PRIMARY KEY CHECK(id=1), name TEXT NOT NULL, consent INTEGER NOT NULL DEFAULT 0)")
                con.execute("INSERT INTO profile VALUES(1, 'Legacy User', 1)")
                con.execute("CREATE TABLE memories(id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, approved INTEGER NOT NULL)")
                con.execute("INSERT INTO memories VALUES(1, 'Old Memory', 'Surviving memory', 1)")
                con.execute("CREATE TABLE reminders(id INTEGER PRIMARY KEY, title TEXT NOT NULL, due_at TEXT NOT NULL, acknowledged INTEGER NOT NULL DEFAULT 0)")
                con.execute("INSERT INTO reminders VALUES(1, 'Old Reminder', '2026-10-30T10:00', 0)")
                con.execute("CREATE TABLE sessions(id INTEGER PRIMARY KEY, correct INTEGER NOT NULL, attempts INTEGER NOT NULL, hints INTEGER NOT NULL, paused INTEGER NOT NULL, level INTEGER NOT NULL, recommendation TEXT NOT NULL, next_level INTEGER NOT NULL, model_action TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
                con.execute("INSERT INTO sessions VALUES(1, 3, 3, 0, 0, 1, 'advance', 2, 'advance', '2026-10-25 10:00:00')")
                con.commit()

            # Run migration on legacy database
            from Backend.app import migrate
            with sqlite3.connect(legacy_db) as con:
                con.row_factory = sqlite3.Row
                migrate(con)
                con.commit()

                # Verify existing records survived untouched
                p = con.execute("SELECT * FROM profile WHERE id=1").fetchone()
                self.assertEqual(p['name'], 'Legacy User')
                self.assertEqual(p['consent'], 1)
                self.assertEqual(p['auto_apply_plan'], 0)

                m = con.execute("SELECT * FROM memories WHERE id=1").fetchone()
                self.assertEqual(m['title'], 'Old Memory')

                r = con.execute("SELECT * FROM reminders WHERE id=1").fetchone()
                self.assertEqual(r['title'], 'Old Reminder')

                s = con.execute("SELECT * FROM sessions WHERE id=1").fetchone()
                self.assertEqual(s['recommendation'], 'advance')

                plan = con.execute("SELECT * FROM next_plan WHERE id=1").fetchone()
                self.assertIsNotNone(plan)
                self.assertEqual(plan['target_level'], 1)
        finally:
            try:
                if legacy_db.exists():
                    legacy_db.unlink()
            except Exception:
                pass

    def test_group_separation(self):
        report = json.loads((PROJECT_ROOT / 'ML/artifacts/evaluation.json').read_text(encoding='utf-8'))
        train_p = set(report['train_participants'])
        test_p = set(report['test_participants'])
        self.assertFalse(train_p & test_p, 'Participant overlap detected!')
        self.assertEqual(report['train_rows'], 768)
        self.assertEqual(report['test_rows'], 192)

if __name__ == '__main__':
    unittest.main()
