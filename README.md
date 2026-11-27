# Assignment 1: Personal Chat with an Answer Evaluator and an Improvement Loop (Actor-Critic)
Rafael Mishayev - 318628716, Shon Horshid - 209064450, Ron Levi - 322926940

A chat application that represents a person based on background information. For every question, the **Actor**
produces a draft answer and the **Critic** checks it against the sources. An approved answer is shown to the user.
A rejected answer goes back to the Actor together with feedback for correction, up to **3 attempts** per question.

> **The profile in this project is a fictional sample profile** (Dana Levi). It was created for this assignment and is
> marked as such in the background files.

## Requirements

- Python **3.12** (tested with 3.12.0)
- A Google Gemini API key (`GOOGLE_API_KEY`)

## Installation

From the project folder (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS or Linux, use `source .venv/bin/activate` instead of the activation line.

## Environment setup

1. Copy `.env.example` to a file named `.env`.
2. Fill in `GOOGLE_API_KEY` with your own key.

```powershell
Copy-Item .env.example .env
```

API keys are read from environment variables only (through `.env`). The `.env` file is not part of the submission and
is listed in `.gitignore`. Variable names: `GOOGLE_API_KEY`, and optionally `ACTOR_MODEL` and `CRITIC_MODEL`.

## Running the chat

```powershell
python app.py
```

Open the address printed in the terminal (usually `http://127.0.0.1:7860`).
The chat shows only the user's messages and the final approved answers. Drafts, evaluator decisions and feedback are
saved to a JSON log in the `logs/` folder.

## Running the tests

| Command | What it does |
|---|---|
| `python run_scenarios.py` | Runs the **five scenarios** of part D and saves the results to `results/` |
| `python run_scenarios.py 4` | Runs a single scenario (several numbers can be given) |
| `python test_evaluator.py` | Four basic evaluator cases (approval and rejection) |
| `python test_hard_cases.py` | Nine hard evaluator cases (wrong number, wrong year, follow-up questions, and more) |

The tests call Gemini for real, so they need a valid key and a network connection.
On a free key, 429 or 503 errors may occur. The code retries automatically (see below), and if the failure persists it
is recorded as a technical error.

## Models and settings

| Component | Model | Notes |
|---|---|---|
| **Actor** (generator) | `gemini-3.5-flash-lite` | Default, can be changed with `ACTOR_MODEL` |
| **Critic** (evaluator) | `gemini-3.1-flash-lite` | Default, can be changed with `CRITIC_MODEL` |

- Both roles use the same provider (Google Gemini) through its OpenAI-compatible endpoint:
  `https://generativelanguage.googleapis.com/v1beta/openai/`. Each role has its own call and its own prompts.
- Sampling parameters (temperature etc.) were not set, so the model defaults are used.
- Maximum attempts per question: **3** (including the first answer), set in `loop.py` (`MAX_ATTEMPTS`).
- The evaluator output is structured: `client.beta.chat.completions.parse(..., response_format=Evaluation)`, validated
  with Pydantic.
- Retries on temporary errors (429, 5xx, network errors) are implemented in `retry.py`: up to 3 retries, waiting
  3, 8 and 15 seconds. These retries happen at the network level and are not counted as generation attempts of the loop.

## Project structure

| File or folder | Purpose |
|---|---|
| `data/linkedin.txt`, `data/summary.txt` | Background sources (sample profile) |
| `context.py` | Loads the sources and builds the Actor's system prompt |
| `actor.py` | `generate()`: the Actor. On a correction attempt it receives the rejected answer and the feedback |
| `evaluator.py` | The `Evaluation` schema, the System Evaluator and User Evaluator, and `evaluate()` |
| `loop.py` | The generate-evaluate-fix loop and the JSON log |
| `retry.py` | Retries on temporary errors |
| `app.py` | `chat()` and the Gradio interface |
| `run_scenarios.py`, `test_evaluator.py`, `test_hard_cases.py` | The tests |
| `architecture_diagram.svg` | Architecture diagram |
| `logs/` | One JSON log per question (drafts, decisions, feedback, status) |
| `results/` | Results of the five scenarios |
| `screenshots/` | Screenshots of the chat and of the test runs |
| `report.docx` | Short report (architecture diagram, feedback example, limitations) |

## How the loop works

1. **Generate:** the Actor receives the sources, the conversation history and the question, and produces a candidate answer.
2. **Evaluate:** the Critic returns an `Evaluation` with `is_acceptable` and `feedback`, and the output is validated
   against the schema.
3. **Approval:** if `is_acceptable` is `True`, the answer is shown and added to the history.
4. **Rejection:** if it is `False` and attempts remain, the Actor receives the rejected answer and the feedback and
   produces a corrected version.
5. **Attempts exhausted:** after a third rejection a message is shown saying that no approved answer was obtained.
   A rejected answer is never shown.
6. **Technical error:** a failed call or unparsable output ends in the `technical_error` state. In the log the
   evaluation is marked as "not completed", with no content decision.

Final statuses in the log: `approved`, `attempts_exhausted`, `technical_error`.
The decision on how to continue relies only on the validated boolean field.

## Scenario results

The result files are in `results/`: `scenario_1.json` to `scenario_5.json`, and `summary.json`.
Each scenario file contains the input, the attempts log, the output shown to the user, and the comparison with the
expected behavior.

| # | Scenario | Type | Matched expectation |
|---|---|---|---|
| 1 | Question about existing information | LLM evaluator | Yes |
| 2 | Follow-up question | LLM evaluator | Yes |
| 3 | Detail not in the sources | LLM evaluator | Yes |
| 4 | Rejection and improvement | LLM evaluator, with a flawed first draft injected on purpose | Yes |
| 5 | Attempts exhausted | **Mock evaluator** that always rejects, with a real Actor | Yes |

Scenario 5 is a control-flow test only and does not measure the quality of the evaluator. The results obtained from the
language model (scenarios 1 to 4) are presented separately from it.
The automatic match check relies on keywords, so it is approximate. The manual check of the claims against the
background files is described in the report.

## Notes

- The history passed to the Actor and the Critic contains user messages and approved answers only. Status messages
  (attempts exhausted or error) and the question that preceded them are removed from it.
- Pydantic validation checks structure only. It does not guarantee that the evaluator's decision is correct.
