# Antigravity: step-by-step setup

## 1. Extract the project
Extract Memory_Companion_Project.zip. Open the inner `Memory_Companion` folder containing this file, requirements.txt and the three main folders. Avoid opening only Frontend or Backend.

## 2. Prepare Python
Use Python 3.12 (recommended for the included model). On Windows, install Python with PATH enabled if needed. Check in Antigravity's terminal:
```powershell
python --version
```
If Windows only recognises `py`, use `py -3.12` for the venv command below. Linux may use `python3` for that first command. After activation, use `python`.

## 3. Create an environment
Windows PowerShell:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```
If activation is blocked, no policy change is needed; use the environment executable directly:
```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m ML.generate_data
.venv\Scripts\python.exe -m ML.train
.venv\Scripts\python.exe -m Backend.app
```
Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```
Select `.venv` as the IDE's Python interpreter if available. Installation needs internet; running locally afterward does not.

## 4. Generate and train
Run from the project root, never from inside ML:
```bash
python -m ML.generate_data
python -m ML.train
```
This creates 960 rows, keeps participants separate in an 80/20 participant split, trains the Random Forest and saves model.joblib plus evaluation.json in ML/artifacts. A pre-trained copy is included, but retraining in your own environment is recommended. Training is small and CPU-only. Expected output has 768 training rows and 192 test rows. The delivered run achieved 99.48% synthetic holdout accuracy; do not describe that as patient accuracy.

## 5. Start the app
```bash
python -m Backend.app
```
Open http://127.0.0.1:8000. Keep this terminal running. This single server hosts both frontend and backend; do not launch index.html by double clicking or use a separate Live Server.

## 6. Set up the demonstration
1. Open Caregiver. Keep a fictional participant name, tick the permission checkbox only for your authorised demonstration, and save.
2. Add a fictional familiar memory and approve it. Unapproved entries stay out of the participant's memory book.
3. Add a one-time reminder with a local date/time. Open Reminders and mark it done when appropriate.
4. Open Matching game. Start level 1. Turn over cards, find pairs, or try a hint.
5. Finish and save. At least three pair attempts are needed for a difficulty suggestion. You may finish a short game, but it produces insufficient evidence.
6. Open Caregiver. Compare the rule action with the real Random Forest output in the session table. Approve the next suggested level explicitly.
7. Start the next game. Levels change the number of pairs. At levels 1 and 3, suggestions remain within bounds.
8. To rest, press Pause & save. Gameplay freezes immediately; choose Resume activity or Save paused activity. Saving ends that round; starting a new round resets the cards and counters.
9. Refresh the page to verify database persistence. Refreshing during an unsaved game loses that round; it does not invent a saved session.

## 7. Verify
Stop the server with Ctrl+C if desired, then run:
```bash
python -m unittest discover -s tests -v
```
The test suite uses its own temporary database. Visit /api/health to confirm model_loaded is true. If false, retrain and restart.

## 8. Use Antigravity
Open `ANTIGRAVITY_MASTER_PROMPT.md`, copy its complete contents into the Antigravity agent panel, and ask it to work in this existing folder. The prompt directs it to inspect, run and improve this project, rather than replacing it with an unrelated stack. Paste errors into the agent when necessary; verify each completed change by running the app and tests.

## 9. Troubleshooting
- ModuleNotFoundError Backend: your terminal is in the wrong folder. Return to Memory_Companion and use `python -m Backend.app`.
- Missing sklearn/pandas: activate .venv and install requirements using that Python.
- Model version mismatch: regenerate data, retrain with the installed environment, and restart the server.
- Port 8000 occupied: Windows PowerShell `$env:PORT="8001"`, then `python -m Backend.app`. Linux: `PORT=8001 python -m Backend.app`. Open the matching port in your browser.
- Save blocked: review and save the permission setting in Caregiver. Game remains available without saving consent.
- Cannot change level: finish the active activity, or resume and finish a paused activity.
- Speech silent: tick Spoken cues; voices depend on browser/OS and are optional. Core gameplay does not depend on audio.
- No reminder popup: this version displays reminders inside the app, with no background OS notifications.
- Reset demonstration: stop server, remove Backend/memory.db, restart. This deletes all demo records.

## 10. Suggested next development order
Improve accessibility with supervised usability feedback; then add memory editing/deletion, profile-specific data and real caregiver authentication. Add reviewed regional language content later. Keep additional games, PWA support, encrypted storage and clinical studies as separate future work. The supplied implementation makes no claim to cover these yet.
