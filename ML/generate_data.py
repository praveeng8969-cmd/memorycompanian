"""Reproducible synthetic data only. No real patient records."""
import csv, random
from pathlib import Path
from Backend.policy import action
OUT=Path(__file__).parent/'data/synthetic_sessions.csv'
def generate():
    rng=random.Random(42);rows=[]
    for participant in range(1,121):
        ability=max(.2,min(.98,rng.gauss(.7,.15)))
        for _ in range(8):
            attempts=rng.choice([5,8,10,12]);level=rng.randint(1,3)
            correct=sum(rng.random()<ability-(level-1)*.08 for _ in range(attempts))
            hints=sum(rng.random()<max(.05,.65-ability) for _ in range(attempts))
            paused=int(rng.random()<.08);acc=correct/attempts;hint=hints/attempts
            rows.append(dict(participant_id=participant,activity='matching',level=level,accuracy=acc,hint_rate=hint,paused=paused,recommended_action=action(acc,hint,paused)))
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    print(f'Generated {len(rows)} synthetic sessions from 120 synthetic participants: {OUT}')
if __name__=='__main__': generate()
