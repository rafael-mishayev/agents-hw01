import os

from dotenv import load_dotenv
from openai import OpenAI

from context import TWIN_SYSTEM_PROMPT
from retry import call_with_retry

load_dotenv(override=True)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# max_retries=0: retries are handled explicitly by call_with_retry
gemini = OpenAI(api_key=os.getenv("GOOGLE_API_KEY"), base_url=GEMINI_BASE_URL, max_retries=0)

ACTOR_MODEL = os.getenv("ACTOR_MODEL", "gemini-3.5-flash-lite")

system = [{"role": "system", "content": TWIN_SYSTEM_PROMPT}]


def generate(message, history, rejected=None, feedback=None):
    """Actor: produce a candidate answer.

    history holds ONLY user messages and approved final answers.
    When `rejected` and `feedback` are given, the Actor receives its rejected
    answer together with the Critic's feedback and must write a corrected version.
    """
    user_content = message
    if rejected is not None:
        user_content += (
            "\n\n---\nYour previous answer to this question was REJECTED by a reviewer.\n"
            f"Rejected answer:\n{rejected}\n\n"
            f"Reviewer feedback:\n{feedback}\n\n"
            "Write a corrected answer to the user's question above, fixing every problem "
            "the reviewer pointed out. Answer only with the corrected answer."
        )
    messages = system + history + [{"role": "user", "content": user_content}]
    response = call_with_retry(gemini.chat.completions.create, model=ACTOR_MODEL, messages=messages)
    return response.choices[0].message.content
