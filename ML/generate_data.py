"""Reproducible synthetic demonstration data generator matching the report policy.

No real patient records are used.
"""
import csv, random
from pathlib import Path
from Backend.policy import action

OUT = Path(__file__).parent / 'data/synthetic_sessions.csv'

def generate():
    rng = random.Random(42)
    rows = []
    for participant in range(1, 121):
        ability = max(0.2, min(0.98, rng.gauss(0.7, 0.15)))
        for _ in range(8):
            # Sessions meet the 5-attempt threshold requirement
            attempts = rng.choice([5, 8, 10, 12])
            level = rng.randint(1, 3)
            correct = sum(rng.random() < ability - (level - 1) * 0.08 for _ in range(attempts))
            hints = sum(rng.random() < max(0.05, 0.65 - ability) for _ in range(attempts))
            paused = int(rng.random() < 0.08)
            acc = correct / attempts
            hint = hints / attempts
            act = action(acc, hint, paused, attempts)
            rows.append(dict(
                participant_id=participant,
                activity='matching',
                level=level,
                accuracy=acc,
                hint_rate=hint,
                paused=paused,
                recommended_action=act
            ))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f'Generated {len(rows)} synthetic sessions from 120 synthetic participants: {OUT}')

if __name__ == '__main__':
    generate()
