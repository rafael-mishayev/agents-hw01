import json
import time
import uuid
from pathlib import Path

from actor import ACTOR_MODEL, generate
from evaluator import CRITIC_MODEL, EvaluationError, evaluate

MAX_ATTEMPTS = 3  # including the first answer

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

NO_APPROVED_MESSAGE = "לא התקבלה תשובה מאושרת במסגרת מגבלת הניסיונות. אפשר לנסח את השאלה מחדש."
TECH_ERROR_MESSAGE = "אירעה שגיאה טכנית ולא ניתן היה להשלים את בדיקת התשובה. נסו שוב מאוחר יותר."

# Final statuses of a question
APPROVED = "approved"
ATTEMPTS_EXHAUSTED = "attempts_exhausted"
TECHNICAL_ERROR = "technical_error"


def save_log(log):
    """Write the per-question log as JSON. Drafts and feedback live ONLY here, never in the chat."""
    # timestamp + short random suffix, so fast consecutive questions never overwrite each other
    path = LOG_DIR / f"{log['scenario_id']}_{int(time.time())}_{uuid.uuid4().hex[:6]}.json"
    path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    log["log_file"] = str(path)
    return log


def answer_question(message, history, scenario_id="chat", first_draft=None, evaluator=evaluate, generator=generate):
    """Generate -> evaluate -> (fix) loop, at most MAX_ATTEMPTS generations.

    history: user messages and approved final answers only.
    first_draft / evaluator / generator can be injected for controlled tests.
    Returns (text_for_user, log). text_for_user is an approved answer ONLY when
    log["status"] == "approved"; otherwise it is a status message.
    """
    # Record which models produced this log (an injected test double is marked explicitly)
    models = {
        "actor": ACTOR_MODEL if generator is generate else "injected test generator",
        "critic": CRITIC_MODEL if evaluator is evaluate else "injected test evaluator (mock)",
    }
    log = {"scenario_id": scenario_id, "question": message, "models": models, "status": None, "attempts": []}
    rejected = feedback = None

    # A new question always starts from attempt 1 (the counter is local to this call)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        entry = {"attempt": attempt}

        # 1) Generate (or use the injected draft for the first attempt)
        try:
            if attempt == 1 and first_draft is not None:
                candidate = first_draft
            else:
                candidate = generator(message, history, rejected, feedback)
        except Exception as e:
            entry.update(candidate=None, evaluation="not completed", error=f"generation failed: {e}")
            log["attempts"].append(entry)
            log["status"] = TECHNICAL_ERROR
            save_log(log)
            return TECH_ERROR_MESSAGE, log
        entry["candidate"] = candidate

        # 2) Evaluate. The result is validated against the Evaluation schema.
        try:
            evaluation = evaluator(message, history, candidate)
        except EvaluationError as e:
            # No content decision exists: record that the evaluation was not completed
            entry.update(evaluation="not completed", error=str(e))
            log["attempts"].append(entry)
            log["status"] = TECHNICAL_ERROR
            save_log(log)
            return TECH_ERROR_MESSAGE, log
        entry.update(is_acceptable=evaluation.is_acceptable, feedback=evaluation.feedback)
        log["attempts"].append(entry)

        # 3) Decide ONLY by the validated boolean
        if evaluation.is_acceptable:
            log["status"] = APPROVED
            log["final_answer"] = candidate
            save_log(log)
            return candidate, log

        # 4) Rejected: the next generation receives the rejected answer and the feedback
        rejected, feedback = candidate, evaluation.feedback

    # 5) Attempts exhausted: never present a rejected answer as approved
    log["status"] = ATTEMPTS_EXHAUSTED
    save_log(log)
    return NO_APPROVED_MESSAGE, log
