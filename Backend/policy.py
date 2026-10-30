"""Transparent demonstration adaptation policy matching the report specification.

Not a diagnostic or clinical instrument.
"""

LEVEL_CONFIG = {
    1: {
        "level": 1,
        "name": "Gentle",
        "pairs_per_board": 3,
        "total_boards": 2,
        "description": "3 pairs per board · 2 planned boards (up to 6 pair attempts)",
    },
    2: {
        "level": 2,
        "name": "Steady",
        "pairs_per_board": 4,
        "total_boards": 2,
        "description": "4 pairs per board · 2 planned boards (up to 8 pair attempts)",
    },
    3: {
        "level": 3,
        "name": "More pairs",
        "pairs_per_board": 5,
        "total_boards": 1,
        "description": "5 pairs per board · 1 planned board (up to 5 pair attempts)",
    },
}

def get_level_config(level):
    clamped = max(1, min(3, int(level)))
    return LEVEL_CONFIG[clamped]

def action(accuracy, hint_rate, paused, attempts=5):
    """Evaluate session measures strictly following the report's ordered policy rules."""
    if paused:
        return 'pause'
    if attempts < 5:
        return 'insufficient_evidence'
    if accuracy < 0.50 or hint_rate > 0.50:
        return 'simplify'
    if accuracy >= 0.85 and hint_rate <= 0.20:
        return 'advance'
    return 'maintain'

def recommend(correct, attempts, hints, level, paused):
    """Determine adaptive recommendation, next level, reassuring participant guidance,

    and transparent caregiver explanation.
    """
    level = max(1, min(3, int(level)))

    # Rule 1: Paused session
    if paused:
        reason = "Take a break. Continue when you and your caregiver are ready."
        caregiver_reason = "Activity was paused. Level held unchanged; explicit resume decision required."
        return 'pause', level, reason, caregiver_reason, get_level_config(level)

    # Rule 2: Fewer than 5 genuine attempts
    if attempts < 5:
        reason = "We'll keep this level for now."
        caregiver_reason = f"Fewer than 5 attempts recorded ({attempts}/5). Level held unchanged pending sufficient evidence."
        return 'insufficient_evidence', level, reason, caregiver_reason, get_level_config(level)

    # Calculate metrics with zero-division safeguard
    accuracy = correct / attempts if attempts > 0 else 0.0
    hint_rate = min(hints / attempts, 1.0) if attempts > 0 else 0.0

    # Rule 3: Simplification threshold
    if accuracy < 0.50 or hint_rate > 0.50:
        a = 'simplify'
        next_level = max(1, level - 1)
        if next_level < level:
            reason = "Let's try fewer pairs with a little more help."
            caregiver_reason = f"Support needed (accuracy {accuracy:.0%}, hint rate {hint_rate:.0%}). Suggested level reduced to {next_level}."
        else:
            reason = "Let's stay at this gentle level with extra guidance."
            caregiver_reason = f"Support needed at minimum level 1 (accuracy {accuracy:.0%}, hint rate {hint_rate:.0%}). Level maintained at 1 with extra visual support."

    # Rule 4: Advancement threshold
    elif accuracy >= 0.85 and hint_rate <= 0.20:
        a = 'advance'
        next_level = min(3, level + 1)
        if next_level > level:
            reason = "You matched these comfortably. Your next activity has a few more pairs."
            caregiver_reason = f"High performance (accuracy {accuracy:.0%}, hint rate {hint_rate:.0%}). Suggested level increased to {next_level}."
        else:
            reason = "You matched these comfortably at the highest level. We will maintain this gentle challenge."
            caregiver_reason = f"High performance at ceiling level 3 (accuracy {accuracy:.0%}, hint rate {hint_rate:.0%}). Level maintained at maximum level 3."

    # Rule 5: Maintain
    else:
        a = 'maintain'
        next_level = level
        reason = "Let's enjoy another activity at this comfortable level."
        caregiver_reason = f"Comfortable engagement within standard range (accuracy {accuracy:.0%}, hint rate {hint_rate:.0%}). Current level {level} maintained."

    return a, next_level, reason, caregiver_reason, get_level_config(next_level)
