# Verification of the delivered package

Completed on 26 October 2026 using Python 3.12.14, Pandas 2.2.3, scikit-learn 1.8.0 and Joblib 1.5.3.

- Data generator: 960 synthetic sessions, 120 synthetic participants.
- Training: 768 rows from 96 participants; holdout: 192 rows from 24 disjoint participants.
- Holdout accuracy: 0.9947916667 (99.48%). This measures synthetic rule imitation only.
- `python -m unittest discover -s tests -v`: 3 tests passed. Tests cover policy boundaries, consent denial/revocation, database persistence, actual HTTP model inference, malformed counts/booleans/levels, reminder acknowledgement and participant split isolation.
- `node --check Frontend/app.js`: passed JavaScript syntax verification.
- Browser automation was attempted but the Chromium download was unavailable/corrupt in this environment. No visual or interactive browser verification is claimed. Follow the manual demonstration in STEP_BY_STEP.md.

The delivered database is absent by design. Starting the server creates a fresh database with a fictional profile and recording permission disabled. The trained model, generated CSV, evaluation report and source files are included. Model results are not copied from the uploaded report.
