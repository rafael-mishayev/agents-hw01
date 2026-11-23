import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from context import NAME, linkedin, summary
from retry import call_with_retry

load_dotenv(override=True)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# max_retries=0: retries are handled explicitly by call_with_retry
gemini = OpenAI(api_key=os.getenv("GOOGLE_API_KEY"), base_url=GEMINI_BASE_URL, max_retries=0)

CRITIC_MODEL = os.getenv("CRITIC_MODEL", "gemini-3.1-flash-lite")


class EvaluationError(Exception):
    """Technical failure of the evaluation step (not a content decision)."""


class Evaluation(BaseModel):
    """Structured output of the Critic. Both fields are required."""

    is_acceptable: bool  # decision: does the answer meet the criteria?
    feedback: str  # short reasoning; on rejection: the problem + how to fix it


# System Evaluator: defines the role and the decision criteria
evaluator_system_prompt = f"""

# Your role

You are an evaluator. A chat assistant represents {NAME} on a personal website and answers visitors' questions.
You receive the visitor's question, the conversation history, and the assistant's candidate answer.
You decide whether the candidate answer is acceptable.

# Sources

The only valid sources of facts about {NAME} are the following two documents.

## Personal summary

{summary}

## LinkedIn profile

{linkedin}

# Criteria

The answer is acceptable only if ALL of the following criteria hold:

1. Grounding in sources: every fact about {NAME} (education, jobs, skills, projects, numbers, dates, hobbies)
   is supported by the sources. Any invented achievement, role, employer, date, number or personal detail
   means the answer must be rejected.
2. Answers the question: the answer addresses the user's request and takes the relevant conversation history into account.
3. Missing information: when the sources do not contain the requested information, the answer must clearly say
   that there is not enough information, and must not invent a fact. An answer that rightly says
   "I don't have enough information" IS acceptable. An answer that invents a fact instead IS NOT.
4. Clarity: the answer is clear, to the point, written in Hebrew, in the first person, in 2-5 sentences,
   and follows the style rules of the assistant.
5. Honesty about being an AI: the assistant is an AI digital twin of {NAME}, and it must say so clearly
   when asked (for example "are you a real person?"). An answer that claims to be a real human being,
   or that avoids admitting it is an AI, must be rejected. An answer that clearly says it is an AI digital
   twin of {NAME} is correct, and you must NOT ask the assistant to respond as if it were {NAME} herself.

# Output

Return is_acceptable (true or false) and feedback.
Write the feedback in English, in the third person, addressed to the assistant that wrote the candidate answer
(for example: "The answer claims X, but the sources do not mention it"). You are a reviewer, NOT {NAME}:
never write in the first person as if you were {NAME}.
- If accepted: feedback is a short justification.
- If rejected: feedback must quote the problematic claim or name the missing part, explain why it fails,
  and give a practical instruction for fixing it (for example: remove the claim, or say the information is missing).
Never write vague feedback such as "the answer is not good".
""".strip()


def evaluator_user_prompt(message, history, reply):
    """User Evaluator: the question, the relevant history and the candidate answer."""
    history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history) or "(no previous messages)"
    return f"""
Conversation so far:
{history_text}

User question:
{message}

Candidate answer to evaluate:
{reply}

Evaluate the candidate answer according to the criteria.
""".strip()


def evaluate(message, history, reply) -> Evaluation:
    """Ask the Critic for a structured Evaluation.

    Raises EvaluationError on any technical failure (API error, unparsable output,
    missing required field). A failure is never treated as approval.
    """
    messages = [
        {"role": "system", "content": evaluator_system_prompt},
        {"role": "user", "content": evaluator_user_prompt(message, history, reply)},
    ]
    try:
        response = call_with_retry(
            gemini.beta.chat.completions.parse,
            model=CRITIC_MODEL,
            messages=messages,
            response_format=Evaluation,
        )
        evaluation = response.choices[0].message.parsed
    except Exception as e:  # network/API error, invalid JSON, schema validation error
        raise EvaluationError(f"Evaluation failed: {e}") from e
    if evaluation is None:
        raise EvaluationError("Evaluation failed: the model returned no parsable Evaluation")
    return evaluation
