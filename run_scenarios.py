"""Run the five scenarios of part D and save input, attempts log and displayed output.

Usage:
    python run_scenarios.py        # run all scenarios
    python run_scenarios.py 4      # run only scenario 4
    python run_scenarios.py 1 3    # run scenarios 1 and 3

Results are written to results/scenario_N.json and results/summary.json.
Scenarios 1-4 use the real LLM Critic. Scenario 5 uses a MOCK Critic (control-flow test).
"""

import json
import sys
import time
from pathlib import Path

from evaluator import Evaluation
from loop import NO_APPROVED_MESSAGE, answer_question

sys.stdout.reconfigure(encoding="utf-8")

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

PAUSE_SECONDS = 5  # avoid rate limits between scenarios

# Scenario 4: a controlled flawed first draft with an invented personal fact
FLAWED_DRAFT = "למדתי באוניברסיטת סטנפורד וניהלתי צוות של 40 מהנדסים בגוגל."


def always_reject(message, history, reply):
    """MOCK Critic: rejects every answer. Used only to test the attempt limit."""
    return Evaluation(
        is_acceptable=False,
        feedback="MOCK: rejected on purpose to test the control flow (attempt limit).",
    )


def final_text(log, text):
    """Text shown to the user, with a marker when it is not an approved answer."""
    return text if log["status"] == "approved" else f"[NOT AN APPROVED ANSWER] {text}"


def scenario_1():
    q = "איפה למדת?"
    text, log = answer_question(q, [], scenario_id="s1")
    ok = log["status"] == "approved" and any(k in text for k in ("תל אביב", "בן-גוריון", "בן גוריון"))
    return {
        "name": "Question about existing information",
        "kind": "llm",
        "expected": "Approved answer that cites the supporting detail from the profile (Tel Aviv University / Ben-Gurion University).",
        "inputs": [q],
        "displayed": [final_text(log, text)],
        "logs": [log],
        "matched": ok,
        "note": "Also verify manually that every claim appears in data/linkedin.txt.",
    }


def scenario_2():
    q1 = "באיזה פרויקט עבדת על צ'אטבוט?"
    q2 = "באילו טכנולוגיות השתמשת בו?"  # relies on the previous answer ("בו")
    text1, log1 = answer_question(q1, [], scenario_id="s2_turn1")
    history = []
    if log1["status"] == "approved":
        history = [{"role": "user", "content": q1}, {"role": "assistant", "content": text1}]
    text2, log2 = answer_question(q2, history, scenario_id="s2_turn2")
    uses_context = any(k in text2 for k in ("Python", "Gradio", "embeddings", "PaperPal"))
    ok = log1["status"] == "approved" and log2["status"] == "approved" and uses_context
    return {
        "name": "Follow-up question",
        "kind": "llm",
        "expected": "Both turns approved; the second answer refers to the project from the first answer (PaperPal technologies).",
        "inputs": [q1, q2],
        "displayed": [final_text(log1, text1), final_text(log2, text2)],
        "logs": [log1, log2],
        "matched": ok,
        "note": "The second question is meaningless without the first answer, so a correct answer proves context is kept.",
    }


def scenario_3():
    q = "כמה ילדים יש לך?"
    text, log = answer_question(q, [], scenario_id="s3")
    says_missing = any(k in text for k in ("אין לי", "אין מספיק", "לא נמצא", "אין מידע"))
    ok = log["status"] == "approved" and says_missing
    return {
        "name": "Detail not in the sources",
        "kind": "llm",
        "expected": "Approved answer that says there is not enough information, without inventing a personal fact.",
        "inputs": [q],
        "displayed": [final_text(log, text)],
        "logs": [log],
        "matched": ok,
        "note": "Verify manually that the answer does not state any number of children.",
    }


def scenario_4():
    q = "איפה למדת?"
    text, log = answer_question(q, [], scenario_id="s4", first_draft=FLAWED_DRAFT)
    attempts = log["attempts"]
    first_rejected = bool(attempts) and attempts[0].get("is_acceptable") is False
    fixed = log["status"] == "approved" and len(attempts) >= 2 and "סטנפורד" not in text and "גוגל" not in text
    if attempts and attempts[0].get("is_acceptable") is True:
        note = "FAILURE: the Critic approved the flawed draft. Document it and improve the evaluator prompt."
    else:
        note = "Check that the feedback names the invented facts and that the corrected answer matches the sources."
    return {
        "name": "Rejection and improvement",
        "kind": "llm (flawed first draft injected on purpose)",
        "expected": "Attempt 1 (invented facts) rejected with reasoned feedback; a corrected attempt is evaluated again and approved.",
        "inputs": [q, f"first draft (injected): {FLAWED_DRAFT}"],
        "displayed": [final_text(log, text)],
        "logs": [log],
        "matched": first_rejected and fixed,
        "note": note,
    }


def scenario_5():
    q = "איפה למדת?"
    text, log = answer_question(q, [], scenario_id="s5_mock", evaluator=always_reject)
    ok = (
        log["status"] == "attempts_exhausted"
        and len(log["attempts"]) == 3
        and text == NO_APPROVED_MESSAGE
        and all(a.get("is_acceptable") is False for a in log["attempts"])
    )
    return {
        "name": "Attempts exhausted",
        "kind": "MOCK evaluator (control-flow test, real Actor)",
        "expected": "Three rejected attempts, stop after the third, and the 'no approved answer' message. No rejected draft shown as approved.",
        "inputs": [q],
        "displayed": [text],
        "logs": [log],
        "matched": ok,
        "note": "The Critic is a mock that always rejects. This tests the flow of the loop, not the quality of the LLM Critic.",
    }


SCENARIOS = {1: scenario_1, 2: scenario_2, 3: scenario_3, 4: scenario_4, 5: scenario_5}


def main():
    wanted = [int(a) for a in sys.argv[1:]] or sorted(SCENARIOS)
    for i, n in enumerate(wanted):
        if i > 0:
            time.sleep(PAUSE_SECONDS)
        print("=" * 70)
        result = SCENARIOS[n]()
        result["scenario"] = n
        (RESULTS_DIR / f"scenario_{n}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Scenario {n}: {result['name']}  [{result['kind']}]")
        print("Expected:", result["expected"])
        for q in result["inputs"]:
            print("  input:", q)
        for log in result["logs"]:
            print(f"  log {log['scenario_id']}: status={log['status']}, attempts={len(log['attempts'])}")
            for a in log["attempts"]:
                decision = a.get("is_acceptable", a.get("evaluation"))
                print(f"    attempt {a['attempt']}: is_acceptable={decision}")
                print(f"      candidate: {a.get('candidate')}")
                print(f"      feedback: {a.get('feedback') or a.get('error')}")
        for d in result["displayed"]:
            print("  displayed:", d)
        print("MATCHED EXPECTATION:" , "YES" if result["matched"] else "NO")
        print("Note:", result["note"])

    # Build the summary from ALL saved scenario files, so running a single scenario
    # never drops the others from summary.json
    summary = []
    for path in sorted(RESULTS_DIR.glob("scenario_*.json")):
        saved = json.loads(path.read_text(encoding="utf-8"))
        summary.append(
            {"scenario": saved["scenario"], "name": saved["name"], "kind": saved["kind"], "matched": saved["matched"]}
        )
    summary.sort(key=lambda s: s["scenario"])
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=" * 70)
    for s in summary:
        print(f"Scenario {s['scenario']} ({s['kind']}): {'matched' if s['matched'] else 'DID NOT MATCH'}")


if __name__ == "__main__":
    main()
