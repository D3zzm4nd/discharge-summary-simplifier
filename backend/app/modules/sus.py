"""FR-12: System Usability Scale scoring (10 items, 1-5; odd: a-1, even: 5-a; x2.5)."""
def sus_score(answers):
    if len(answers) != 10 or any((not isinstance(a, int)) or a < 1 or a > 5 for a in answers):
        raise ValueError("SUS needs 10 answers between 1 and 5")
    return sum((a - 1) if i % 2 == 0 else (5 - a) for i, a in enumerate(answers)) * 2.5
