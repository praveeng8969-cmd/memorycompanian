Act as a senior full-stack Python developer and ML engineer. Develop and refine the existing project in this workspace into a reliable, simple academic demonstration. Implement and verify working files; do not stop at a plan or generate only screenshots.

PROJECT
AI-Based Cognitive Gaming and Memory Assistance Platform for Elderly Dementia Patients in NER. Product name: Memory Companion.
Team: PRASITHA VR (722825104173), PRAVEEN G (722825104174).
Purpose: calm cognitive engagement, familiar memory cues, daily reminders and caregiver-reviewed activity personalisation. Never diagnose dementia or predict disease severity.

FIRST ACTIONS
Read README.md, STEP_BY_STEP.md, Backend/app.py, Backend/policy.py, Frontend/app.js, ML/train.py and ML/MODEL_CARD.md. Inspect the actual folder before editing. Preserve working functionality. Explain gaps briefly, implement improvements, run tests and report actual results. Ask only when a requirement cannot reasonably be inferred. Do not deploy publicly or connect external services.

STACK AND STRUCTURE
Keep Frontend/, Backend/, ML/ and tests/ separate. Use semantic HTML, CSS and vanilla JavaScript, a Python standard-library local HTTP server, SQLite, Pandas, scikit-learn and Joblib. Run the complete app with `python -m Backend.app` from the root. No React rewrite, Node build, GPU, LLM API, cloud database or external keys are needed. Use Python 3.12 with the project's requirements. Frontend fetches same-origin /api endpoints.

REQUIRED SCREENS
1. Home: warm welcome, short guidance and large activity buttons.
2. Matching game: actual shuffled pairs, accessible face-down controls, 3/4/5 pairs at levels 1/2/3, accurate match attempts and hints, optional speech, clear supportive feedback, pause/resume, explicit save, and restart without duplicate submissions.
3. Memory book: only caregiver-approved text memories, stored in SQLite. Never insert untrusted HTML.
4. Reminders: caregiver adds a title and local ISO date/time; participant acknowledges it. Clearly mark due and completed reminders. No invented medication doses or background notification claims.
5. Caregiver: fictional local profile and explicit recording permission, add memory, add reminder, recent session table, transparent policy reason, separately labelled ML prediction, and explicit approval before applying a suggested next level.

ACCESSIBILITY
Use calm cream/green colours, strong contrast, body text at least 18 px, 48 px or larger touch controls, visible keyboard focus, ARIA live feedback, labelled forms, responsive layouts and no countdown pressure. Do not rely only on colour or audio. Keep English-only scope visible until real reviewed regional language content is implemented.

DATA AND API
Preserve and document these routes: GET /api/health, GET /api/dashboard, POST /api/profile, POST /api/sessions, POST /api/memories, POST /api/reminders and POST /api/reminders/{id}/acknowledge. Validate integer counts, boolean fields, correct<=attempts, level in 1..3, lengths and dates on the server. Use SQL placeholders, bounded request sizes and same-origin writes. Keep local server bound to 127.0.0.1. Distinguish caregiver UI from authenticated access: this prototype has no role-based login. Use fictional records and do not present it as secure multi-user deployment.

ADAPTATION POLICY
Paused -> pause, unchanged level.
Fewer than 3 pair attempts -> insufficient_evidence, unchanged level.
Accuracy<0.50 OR hint_rate>0.50 -> simplify.
Accuracy>=0.85 AND hint_rate<=0.20 -> advance.
Otherwise -> maintain.
Accuracy=correct/attempts; hint_rate=min(hints/attempts,1). Clamp next level to 1..3. Do not divide by zero. Pause/insufficient evidence must override any suggestion to advance. The rule policy controls the proposed level; Random Forest prediction remains a separate comparison for caregiver review. Suggestions take effect only after explicit caregiver approval and the next new game.

SIMPLE REAL ML
Generate reproducible synthetic CSV data: 120 synthetic participant IDs, 8 sessions each, seed 42, matching activity, level, accuracy, hint_rate, paused and recommended_action. Labels follow the stated synthetic rule. Split by participant using GroupShuffleSplit(test_size=0.2, random_state=42); assert zero participant overlap. Never include participant ID in input features. Fit preprocessing only on training data. Save a Pipeline with numeric preprocessing, one-hot category handling and a small class-balanced RandomForestClassifier(n_estimators=60,max_depth=7,random_state=42,n_jobs=1). Save ML/artifacts/model.joblib and evaluation.json containing actual accuracy, precision/recall/F1, confusion matrix, split counts and versions. Do not fabricate accuracy or copy the report's number. Synthetic performance only measures reproduction of known rules.

Wire the actual saved model to the backend, and show its inference in the caregiver history. If dependencies or model are unavailable, fall back visibly to the rule policy without breaking the app. Restart backend after training. Do not load untrusted serialized model files. Document English/matching-only scope and future clinical validation requirements without making medical claims.

VERIFICATION
Run `python -m ML.generate_data`, `python -m ML.train` and `python -m unittest discover -s tests -v`. Test policy boundaries, zero attempts, pause override, consent denial/revocation, validation, persistence, reminder acknowledgement, group separation, and inference through the API. Manually or with browser automation check matching, hint previews, repeated save prevention, pause/resume, caregiver approval and narrow/mobile layouts. Verify browser console errors and all fetch paths. Use isolated temporary databases for tests.

DELIVER
Finish all code changes, update README and setup instructions, and give exact commands, the local URL, actual test/model results, files changed and remaining limitations. Preserve known working features and avoid describing future features as implemented. No diagnosis, clinical accuracy, NER language support, encrypted multi-user access, closed-browser reminders or PWA claims unless those features are actually implemented and verified.
