# Demonstration Model Card: Memory Companion Adaptation Model

### Task
Recommend adaptive activity actions (`advance`, `maintain`, `simplify`, or `pause`) from synthetic matching-session performance metrics. This is a compact, interpretable Random Forest classifier (60 trees, maximum depth 7), not a large language model or diagnostic tool.

### Training Data
- **Volume:** 960 synthetic sessions across 120 simulated participants (8 sessions per participant). Seed 42.
- **Labels:** Generated using the report's ordered adaptation policy rules in `Backend.policy.action`.
- **Thresholds:** Minimum 5 attempts are required for adaptive recommendation; sessions below 5 attempts are handled as `insufficient_evidence` by the deterministic policy and bypass ML inference.
- **Data Split:** `GroupShuffleSplit` (80% train, 20% test) grouped strictly by `participant_id` (768 training rows from 96 participants; 192 holdout test rows from 24 disjoint participants). Zero participant overlap is asserted.
- **Features:** `['activity', 'level', 'accuracy', 'hint_rate', 'paused']`. The `participant_id` is excluded from feature inputs. Preprocessing uses `StandardScaler` on numeric columns and `OneHotEncoder` on activity. Preprocessor is fitted strictly on training data within a unified `Pipeline`.

### Language and Regional Scope
The current demonstration prototype operates in English. The mention of language in the broader research report reflects future planned localization for North-East Indian regional languages (e.g. Assamese, Meitei/Manipuri, Bengali, Khasi). No regional language translations or multilingual classification models are implemented or claimed in this prototype.

### Clinical and Diagnostic Disclaimer
This model evaluates replication of known hand-crafted policy rules using synthetic simulation data. High synthetic holdout accuracy indicates rule-learning fidelity only. It does **not** evaluate clinical efficacy, cognitive assessment, dementia stage, or medical diagnosis.

### Runtime Integration
The backend loads `model.joblib` once at startup. When a participant completes an activity with at least 5 attempts, the model computes an inference recommendation shown side-by-side in the Caregiver Workspace. The deterministic rule policy governs the durable next-activity plan; the model serves as an educational comparison tool and never overrides caregiver decisions, pauses, or level bounds.
