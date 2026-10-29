"""Transparent demonstration policy; not a clinical instrument."""
def action(accuracy, hint_rate, paused):
    if paused: return 'pause'
    if accuracy < .5 or hint_rate > .5: return 'simplify'
    if accuracy >= .85 and hint_rate <= .2: return 'advance'
    return 'maintain'

def recommend(correct, attempts, hints, level, paused):
    if paused: return 'pause', level, 'You paused. Rest until you and your caregiver are ready.'
    if attempts < 3: return 'insufficient_evidence', level, 'Complete at least three pair attempts before changing level.'
    a = action(correct / attempts, min(hints / attempts, 1), paused)
    next_level = max(1, min(3, level + {'advance':1,'simplify':-1}.get(a,0)))
    reasons = {'advance':'High accuracy with few hints.', 'simplify':'More support may make the activity comfortable.', 'maintain':'Keep the current activity level.'}
    return a, next_level, reasons[a]
