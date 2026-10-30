# Memory Companion Verification Report

**Completed on 30 October 2026** using Python 3.13.14, Pandas 2.2.3, scikit-learn 1.8.0, and Joblib 1.5.3.

---

## 1. Concrete Cause of the Existing Adaptation Problem

Prior to this upgrade, the platform computed adaptation recommendations but suffered from three core architectural disconnects that prevented them from becoming an actual next-activity experience:

1. **Ephemeral Dropdown-Only Mutation:**
   The previous "Approve suggested level" button only updated the temporary value of a `<select id="level">` HTML element in the DOM. Starting an activity merely read whatever integer happened to be selected in that dropdown. No durable activity plan was stored on the server or in SQLite.
2. **Loss of Plan Across Navigation and Reloads:**
   Because recommendations were not persisted as an active plan entity, switching views, reloading the page, or restarting the server completely discarded any approved difficulty level.
3. **The 3-Pair Mathematical Impossibility:**
   Under the report's rule requiring at least 5 pair attempts before advancing difficulty, single-board Level 1 (which contained only 3 pairs) made advancement mathematically impossible for a participant who matched every card without mistake (producing only 3 attempts, permanently triggering `insufficient_evidence`).

**The Solution Implemented:**
- Created a durable `next_plan` table in SQLite tracking `target_level`, `pairs_per_board`, `total_boards`, `status` (`pending`, `approved`, `overridden`), `reason`, `caregiver_reason`, `source_session_id`, and `approved_at`.
- Implemented multi-board sessions: Level 1 (3 pairs × 2 boards = up to 6 attempts), Level 2 (4 pairs × 2 boards = up to 8 attempts), and Level 3 (5 pairs × 1 board = up to 5 attempts).
- Exposed prominent "Your Next Activity" cards on Home and Game screens that directly launch the persisted, approved activity plan.
- Atomic session recording and plan updates with client idempotency keys (`client_session_id`).

---

## 2. Concise List of Changed Files

- [`Backend/policy.py`](file:///c:/Users/LENOVO/Downloads/Memory_Companion_Project/Memory_Companion/Backend/policy.py): Replaced 3-attempt threshold with report's exact 5-attempt threshold; implemented centralized `LEVEL_CONFIG`; ordered policy rules (pause → <5 attempts → simplify → advance → maintain); level boundary ceiling/floor explanations.
- [`Backend/schema.sql`](file:///c:/Users/LENOVO/Downloads/Memory_Companion_Project/Memory_Companion/Backend/schema.sql): Added `next_plan` table; updated `sessions` with `client_session_id`, `boards_completed`, `total_boards`, and `status`; updated `profile` with `auto_apply_plan`; updated `reminders` with `acknowledged_at`.
- [`Backend/app.py`](file:///c:/Users/LENOVO/Downloads/Memory_Companion_Project/Memory_Companion/Backend/app.py): Non-destructive database migration preserving existing data; atomic session save and plan update; idempotency check; endpoints for `/api/plan`, `/api/plan/approve`, `/api/plan/override`, `/api/memories/{id}/update`, `/api/memories/{id}/delete`, `/api/reminders/{id}/update`, and `/api/reminders/{id}/delete`.
- [`Frontend/index.html`](file:///c:/Users/LENOVO/Downloads/Memory_Companion_Project/Memory_Companion/Frontend/index.html): Added "Your Next Activity" card on Home; active plan banner and board indicator on Game; supervision controls (approve plan, caregiver override form, auto-apply demo toggle); memory/reminder management lists with native edit dialogs.
- [`Frontend/style.css`](file:///c:/Users/LENOVO/Downloads/Memory_Companion_Project/Memory_Companion/Frontend/style.css): Cream/green palette, plan cards, status badges (`.badge-ready`, `.badge-pending`, `.badge-overridden`), board indicators, 130px cards, accessible native dialog styles, and responsive mobile layouts.
- [`Frontend/app.js`](file:///c:/Users/LENOVO/Downloads/Memory_Companion_Project/Memory_Companion/Frontend/app.js): Refactored to explicit state model (`idle`, `playing`, `resolving_pair`, `hinting`, `board_completed`, `paused`, `saving`, `completed`); multi-board progression with culturally resonant familiar objects; safe timer cancellation on pause; durable plan synchronization.
- [`ML/generate_data.py`](file:///c:/Users/LENOVO/Downloads/Memory_Companion_Project/Memory_Companion/ML/generate_data.py): Updated synthetic session generation to strictly follow the 5-attempt threshold.
- [`ML/train.py`](file:///c:/Users/LENOVO/Downloads/Memory_Companion_Project/Memory_Companion/ML/train.py): Retrained class-balanced Random Forest pipeline; UTF-8 output encoding; participant separation assertion.
- [`ML/MODEL_CARD.md`](file:///c:/Users/LENOVO/Downloads/Memory_Companion_Project/Memory_Companion/ML/MODEL_CARD.md): Documented 5-attempt eligibility, English prototype scope, and transparent regional language roadmap.
- [`tests/test_project.py`](file:///c:/Users/LENOVO/Downloads/Memory_Companion_Project/Memory_Companion/tests/test_project.py): 14 comprehensive tests covering report boundaries, insufficient evidence, level clamping, pause precedence, multi-board sessions, idempotency, plan approval, overrides, auto-apply safeguards, non-destructive migration, and ML group separation.
- [`run.py`](file:///c:/Users/LENOVO/Downloads/Memory_Companion_Project/run.py): Convenience launcher supporting execution from workspace root.
- [`README.md`](file:///c:/Users/LENOVO/Downloads/Memory_Companion_Project/Memory_Companion/README.md): Updated architecture, multi-board session workflow, API documentation, and demonstration instructions.

---

## 3. Setup and Run Commands

```powershell
# 1. From workspace root, start the application:
python run.py

# Or from the Memory_Companion directory:
cd Memory_Companion
python -m Backend.app
```

The application will start on **http://127.0.0.1:8000** (or automatically fallback to **8001** if 8000 is occupied).

To run data generation, training, and the test suite:
```powershell
python -m ML.generate_data
python -m ML.train
python -m unittest discover -s tests -v
```

---

## 4. Test Execution Results

Command:
```bash
python -m unittest discover -s tests -v
```

Output:
```text
test_auto_apply_setting_safeguards (test_project.APITests.test_auto_apply_setting_safeguards) ... ok
test_caregiver_override (test_project.APITests.test_caregiver_override) ... ok
test_consent_denial_and_revocation (test_project.APITests.test_consent_denial_and_revocation) ... ok
test_group_separation (test_project.APITests.test_group_separation) ... ok
test_health_and_endpoints (test_project.APITests.test_health_and_endpoints) ... ok
test_idempotency_duplicate_save (test_project.APITests.test_idempotency_duplicate_save) ... ok
test_memories_and_reminders_crud (test_project.APITests.test_memories_and_reminders_crud) ... ok
test_non_destructive_migration (test_project.APITests.test_non_destructive_migration)
Verify that older databases missing new columns survive migration cleanly. ... ok
test_plan_persistence_and_approval_flow (test_project.APITests.test_plan_persistence_and_approval_flow)
Verify that recommendations generate durable plans requiring caregiver approval by default. ... ok
test_insufficient_evidence_threshold (test_project.PolicyTests.test_insufficient_evidence_threshold)
Verify that fewer than 5 attempts always result in insufficient_evidence. ... ok
test_level_limits_and_clamping (test_project.PolicyTests.test_level_limits_and_clamping)
Level limits must stay within 1..3 and clearly explain ceiling/floor. ... ok
test_multi_board_genuine_attempts (test_project.PolicyTests.test_multi_board_genuine_attempts)
A perfect level-1 activity across two boards gives 6 genuine attempts and can advance. ... ok
test_pause_precedence (test_project.PolicyTests.test_pause_precedence)
Any paused session must return pause and retain current level. ... ok
test_report_ordered_rules_and_boundaries (test_project.PolicyTests.test_report_ordered_rules_and_boundaries)
Verify report policy boundaries and conditions. ... ok

----------------------------------------------------------------------
Ran 14 tests in 12.398s

OK
```

Frontend syntax verification:
```bash
node --check Frontend/app.js
# Exited with code 0 (clean syntax)
```

---

## 5. Short Demonstration Procedure

1. **Advance Scenario (Level 1 → Level 2):**
   - In Caregiver view, enable consent and click **Save profile**.
   - On Home screen, click **Start next activity** (Level 1, 2 boards planned).
   - Board 1 (3 pairs): Match all 3 pairs with 0 hints (3 attempts). Click **Continue to next board**.
   - Board 2 (3 pairs): Match all 3 pairs with 0 hints (total 6 attempts, 100% accuracy, 0% hints).
   - Click **Finish & save activity**.
   - Result: Recommendation is `advance`. In Caregiver view, plan is pending Level 2.
   - Click **Approve suggested plan for next activity**.
   - On Home, "Your Next Activity" now shows Level 2 (Steady, 4 pairs/board).

2. **Simplify Scenario (Level 2 → Level 1):**
   - Start Level 2 (Board 1: 4 pairs).
   - Request 3 hints and make 4 mismatch attempts (hint rate > 50%).
   - Click **Finish & save activity**.
   - Result: Recommendation is `simplify`. Next plan suggests Level 1 ("Let's try fewer pairs with a little more help").

3. **Maintain Scenario (Level 2 → Level 2):**
   - Start Level 2.
   - Complete 5 attempts with 70% accuracy (within the 50%-84% range) and 1 hint.
   - Click **Finish & save activity**.
   - Result: Recommendation is `maintain`. Next plan maintains Level 2.

4. **Pause Scenario:**
   - During any active activity, click **Pause activity**.
   - Game freezes; mismatch and hint timers are immediately cancelled.
   - Click **Save paused activity**.
   - Result: Recommendation is `pause`. Target level is held unchanged; explicit resume required.

5. **Insufficient Evidence Scenario:**
   - Start Level 1 (Board 1: 3 pairs).
   - Complete Board 1 (3 attempts), but immediately click **Finish & save activity** without playing Board 2.
   - Result: 3 attempts < 5 threshold → Recommendation is `insufficient_evidence`. Level remains unchanged.

---

## 6. Demonstration Model Results

- **Data Generator:** 960 sessions, 120 simulated participants (8 sessions each).
- **Partition:** 80% train (768 sessions, 96 participants), 20% holdout (192 sessions, 24 disjoint participants). Asserted zero participant overlap.
- **Holdout Accuracy:** 99.48% (Macro avg F1: 0.996).
- **ML Scope Note:** High synthetic accuracy demonstrates fidelity in learning deterministic policy boundaries from simulated data. It does not measure clinical cognitive change or diagnostic accuracy.
