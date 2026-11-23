import time

from evaluator import EvaluationError, evaluate

PAUSE_SECONDS = 3  # avoid rate limits (429) on the free tier

# Short history used by the follow-up cases
HISTORY = [
    {"role": "user", "content": "ספרי לי על פרויקט של צ'אטבוט שבנית"},
    {"role": "assistant", "content": "בניתי את PaperPal, צ'אטבוט שעונה על שאלות על מאמרים אקדמיים."},
]

# (name, question, history, candidate answer, expected is_acceptable)
CASES = [
    ("wrong number", "מה השגת ב-Lumina Health?", [],
     "בנינו צינור RAG שהפחית טענות מומצאות בסיכומים ב-48%.", False),
    ("wrong year", "מתי סיימת את התואר השני?", [],
     "סיימתי את התואר השני באוניברסיטת תל אביב ב-2022.", False),
    ("wrong tenure", "כמה זמן את ב-Lumina Health?", [],
     "אני עובדת ב-Lumina Health כבר שש שנים.", False),
    ("unsupported skill", "האם את מכירה ראייה ממוחשבת?", [],
     "כן, אני מומחית בראייה ממוחשבת ובניתי מערכות זיהוי תמונה.", False),
    ("wrong title", "מה התפקיד שלך?", [],
     "אני סמנכ\"לית הטכנולוגיות (CTO) של Lumina Health.", False),
    ("does not answer the question", "איפה למדת?", [],
     "אני עובדת כמהנדסת למידת מכונה בכירה ב-Lumina Health.", False),
    ("correct hobby", "מה את עושה בזמן הפנוי?", [],
     "אני אוהבת ריצת שטח, במיוחד בכרמל ובגליל, ומנגנת בפסנתר באופן קליל.", True),
    ("correct follow-up", "כמה כוכבים יש לו ב-GitHub?", HISTORY,
     "ל-PaperPal יש בערך 300 כוכבים ב-GitHub.", True),
    ("wrong follow-up", "כמה כוכבים יש לו ב-GitHub?", HISTORY,
     "ל-PaperPal יש בערך 3,000 כוכבים ב-GitHub.", False),
]

mismatches = 0
for name, question, history, answer, expected in CASES:
    print("=" * 60)
    print(f"[{name}]")
    print("Q:", question)
    print("A:", answer)
    print("expected is_acceptable:", expected)
    try:
        ev = evaluate(question, history, answer)
        match = "OK" if ev.is_acceptable == expected else "MISMATCH"
        if match == "MISMATCH":
            mismatches += 1
        print(f"actual is_acceptable: {ev.is_acceptable}  -> {match}")
        print("feedback:", ev.feedback)
    except EvaluationError as e:
        print("TECHNICAL ERROR:", e)
    time.sleep(PAUSE_SECONDS)

print("=" * 60)
print(f"Mismatches: {mismatches} / {len(CASES)}")
