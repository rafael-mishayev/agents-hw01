from evaluator import EvaluationError, evaluate

# (question, candidate answer, what we expect)
CASES = [
    (
        "איפה למדת?",
        "את התואר השני שלי עשיתי באוניברסיטת תל אביב ואת התואר הראשון בבן-גוריון.",
        "expect: acceptable (supported by the sources)",
    ),
    (
        "איפה למדת?",
        "למדתי באוניברסיטת סטנפורד וניהלתי צוות של 40 מהנדסים בגוגל.",
        "expect: rejected (invented facts)",
    ),
    (
        "כמה ילדים יש לך?",
        "אין לי מספיק מידע על כך, אבל אשמח לספר על הניסיון המקצועי שלי.",
        "expect: acceptable (rightly says there is not enough information)",
    ),
    (
        "כמה ילדים יש לך?",
        "יש לי שלושה ילדים.",
        "expect: rejected (invented personal detail)",
    ),
]

for question, answer, expectation in CASES:
    print("=" * 60)
    print("Q:", question)
    print("A:", answer)
    print(expectation)
    try:
        ev = evaluate(question, [], answer)
        print("is_acceptable:", ev.is_acceptable)
        print("feedback:", ev.feedback)
    except EvaluationError as e:
        print("TECHNICAL ERROR:", e)
