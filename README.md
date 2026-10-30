# Memory Companion
AI-Based Cognitive Gaming and Memory Assistance Platform for Elderly Dementia Patients in NER.

A runnable, local academic prototype prepared from the project report.
Team: PRASITHA VR (722825104173), PRAVEEN G (722825104174).

## Quick Start (Run from this folder or workspace root)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m ML.generate_data
python -m ML.train
python -m Backend.app
```
Or from the outer workspace folder:
```bash
python run.py
```
Open http://127.0.0.1:8000 (or http://127.0.0.1:8001 if port 8000 is occupied). The standard-library Python server serves both the frontend and REST API; Node, npm, GPU, cloud databases, and API keys are not required.

## Key Implemented Features

1. **Durable Adaptive Next-Activity Flow:**
   - Multi-board sessions ensure the report's 5-attempt threshold is achievable at every level:
     - **Level 1 (Gentle):** 3 pairs per board · 2 planned boards (up to 6 pair attempts)
     - **Level 2 (Steady):** 4 pairs per board · 2 planned boards (up to 8 pair attempts)
     - **Level 3 (More pairs):** 5 pairs per board · 1 planned board (up to 5 pair attempts)
   - Performance measures (attempts, correct, hints) aggregate across boards.
   - Sessions and the resulting **next-activity plan** are saved atomically in SQLite.
   - Prominent "Your Next Activity" cards on Home and Game screens launch the approved plan.
   - Refreshing the browser or restarting the server restores the durable plan.
2. **Exact Report Policy Compliance:**
   - Ordered rule evaluation:
     1. `paused` → `pause`, level held unchanged, explicit resume required.
     2. `attempts < 5` → `insufficient_evidence`, level held unchanged.
     3. `accuracy < 0.50` OR `hint_rate > 0.50` → `simplify` (clamped to Level 1).
     4. `accuracy >= 0.85` AND `hint_rate <= 0.20` → `advance` (clamped to Level 3).
     5. Otherwise → `maintain`.
   - Distinct, unmatched card clicks count as attempts. Repeated clicks, hints, and matched cards do not fabricate attempts.
3. **Caregiver Supervision and Override:**
   - Supervised review by default: recommendations generate a `pending` plan requiring caregiver approval before taking effect.
   - Caregiver override allows setting difficulty with a documented reason without erasing original recommendation history.
   - Optional demo toggle: automatic approval of eligible recommendations (default OFF, never auto-advances paused or insufficient-evidence sessions).
4. **Memory Book & Daily Reminders:**
   - Memory book: caregiver can add, edit, approve/hide, and delete memories; only approved entries appear in the participant's view. Sample familiar memories can be seeded.
   - Daily reminders: caregiver adds, edits, and deletes reminders. Participant can mark reminders done, recording `acknowledged_at`.
5. **Class-Balanced Random Forest Demonstration Pipeline:**
   - 960 synthetic sessions, 120 simulated participants (8 sessions each).
   - GroupShuffleSplit (80/20 by participant ID) asserts zero participant leakage.
   - Model inference provides an educational comparison in the Caregiver view without overriding deterministic safety policy rules.

## REST API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Server status, model loaded status, policy version |
| `GET` | `/api/dashboard` | Profile, next plan, memories, reminders, recent 100 sessions |
| `GET` | `/api/plan` | Current durable next-activity plan and level configuration |
| `POST` | `/api/plan/approve` | Caregiver approves pending next-activity plan |
| `POST` | `/api/plan/override` | Caregiver overrides level with `{level, reason}` |
| `POST` | `/api/profile` | Update `{name, consent, auto_apply_plan}` |
| `POST` | `/api/sessions` | Save session with `{client_session_id, correct, attempts, hints, level, paused, boards_completed, total_boards}` |
| `POST` | `/api/memories` | Create memory `{title, description, approved}` |
| `POST` | `/api/memories/{id}/update` | Update memory `{title, description, approved}` |
| `POST` | `/api/memories/{id}/delete` | Delete memory by ID |
| `POST` | `/api/reminders` | Create reminder `{title, due_at}` |
| `POST` | `/api/reminders/{id}/acknowledge` | Participant acknowledges reminder; records timestamp |
| `POST` | `/api/reminders/{id}/update` | Update reminder `{title, due_at}` |
| `POST` | `/api/reminders/{id}/delete` | Delete reminder by ID |

## Verification Suite
```bash
python -m unittest discover -s tests -v
```
All 14 tests pass, covering policy boundaries, zero-attempt sessions, multi-board sessions, idempotency, plan approval, overrides, non-destructive migration, and participant separation.

## Deliberate Prototype Scope & Limitations
- **Academic Demonstration:** Single-device local prototype; no multi-user authentication.
- **Non-Diagnostic:** Activities provide calm cognitive stimulation. Performance scores are not clinical measures of dementia severity, disease staging, or medical diagnosis.
- **Reminders:** Function within the open web application; no closed-browser push notifications are claimed.
