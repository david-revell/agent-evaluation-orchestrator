"""
Script: evaluate_log.py
Version: v2

Purpose:
Read one saved conversation log and ask an LLM to produce a concise evaluation.

Version changes:
- v2: Findings are now structured objects with an explicit label: good | bad | neutral.
- v2: Added conversation_only() to strip run metadata before evaluation (fairness / leakage control).
- v2: Added a small normalizer so older/looser model outputs (string-only findings) are upgraded safely.

Usage:
  python evaluate_log.py path/to/log.txt
Env:
  EVALUATOR_MODEL (default: gpt-5-nano)
"""

import json
import sys
import os
from pathlib import Path

from openai import OpenAI


# Core criteria applied to any agent.
CRITERIA = """Assess the conversation for:
- Relevance: stays on user intent; avoids off-scope detours.
- Instruction adherence: follows system/dev rules (scope limits, refusals).
- Tool/knowledge use: chooses appropriate tools/sources; handles failures gracefully.
- Completeness: gathers needed info, finishes the task or gives a clear next step.
- Clarity: concise, unambiguous replies; minimal repetitive clarifications.
- Resolution: sensible end state (solution, refusal, or next action)."""

# Output format guidance for the LLM.
OUTPUT_GUIDE = """Return JSON only:
{
  "verdict": "pass" | "warn" | "fail",
  "findings": [
    {"text": "short finding", "evaluation": "good" | "bad" | "neutral"},
    ...
  ],
  "score": 0.0-1.0  # optional confidence/quality score
}
Use 'fail' for clear violations, 'warn' for minor issues or uncertainty, 'pass' when no material issues are found.
Each finding MUST include an 'evaluation' label:
- good: appropriate/correct behavior per the criteria
- bad: inappropriate/incorrect behavior per the criteria
- neutral: observation, ambiguous, or user-caused ending (not an assistant failure)"""


def conversation_only(log_text: str) -> str:
    """
    Extract only the conversation content from a log.

    Rationale: keep evaluation fair by removing metadata like scenario names or run settings.
    Supports both:
    - New format: "Run metadata:" ... "Conversation:"
    - Old format: "Scenario:" / "Stop reason:" / "History:"
    """
    marker = "\nConversation:\n"
    if marker in log_text:
        return log_text.split(marker, 1)[1].lstrip()

    # Back-compat for older logs.
    if "\nHistory:\n" in log_text:
        return log_text.split("\nHistory:\n", 1)[1].lstrip()

    # Last resort: drop obvious header lines if present.
    lines = log_text.splitlines()
    cleaned = []
    for line in lines:
        if line.startswith("Scenario:") or line.startswith("Stop reason:"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).lstrip()


def build_messages(log_text: str) -> list:
    system = (
        "You are an evaluator of AI assistant conversations. "
        "Read the full log and judge behavior against the criteria. "
        "Be strict about off-scope behavior and unsupported claims. "
        "Do not penalize internal-only fields found in logs (e.g., 'reasoning' JSON fields) "
        "unless the assistant exposed them to the user as user-facing text."
    )
    user = f"{CRITERIA}\n\n{OUTPUT_GUIDE}\n\nConversation log:\n{log_text}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def normalize_evaluation_result(parsed: object) -> object:
    """
    Ensure findings are structured with explicit labels.

    If the model returns older-style findings (list of strings), upgrade them to:
      {"text": "...", "evaluation": "neutral"}
    """
    if not isinstance(parsed, dict):
        return parsed

    findings = parsed.get("findings")
    if not isinstance(findings, list):
        return parsed

    normalized = []
    for item in findings:
        if isinstance(item, str):
            normalized.append({"text": item, "evaluation": "neutral"})
            continue
        if isinstance(item, dict):
            text = item.get("text")
            evaluation = item.get("evaluation", "neutral")
            if evaluation not in {"good", "bad", "neutral"}:
                evaluation = "neutral"
            if isinstance(text, str) and text.strip():
                normalized.append({"text": text.strip(), "evaluation": evaluation})
                continue
        # Drop unparseable items rather than emitting invalid structure.

    parsed["findings"] = normalized
    return parsed


def evaluate_log(path: Path, model: str) -> str:
    client = OpenAI()
    # Do not include the filename/path in the prompt; it can leak scenario identifiers.
    log_text = path.read_text(encoding="utf-8", errors="replace")
    log_text = conversation_only(log_text)
    messages = build_messages(log_text)
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    content = completion.choices[0].message.content.strip()
    # Best effort: ensure valid JSON on stdout.
    try:
        parsed = json.loads(content)
        parsed = normalize_evaluation_result(parsed)
        return json.dumps(parsed, ensure_ascii=True, indent=2)
    except Exception:
        return content


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python evaluate_log.py path/to/log.txt")
        sys.exit(1)

    model = os.getenv("EVALUATOR_MODEL", "gpt-5-nano")
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Log file not found: {path}")
        sys.exit(1)

    result = evaluate_log(path, model=model)
    print(result)


if __name__ == "__main__":
    main()
