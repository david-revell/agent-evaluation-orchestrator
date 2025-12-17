"""
Simple log evaluator.

Reads one conversation log file and asks an LLM to produce a concise evaluation.
Output: JSON with verdict (pass|warn|fail), findings (bullets), and optional score [0,1].
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
  "findings": ["short bullet 1", "short bullet 2", ...],
  "score": 0.0-1.0  # optional confidence/quality score
}
Use 'fail' for clear violations, 'warn' for minor issues or uncertainty, 'pass' when no material issues are found."""


def build_messages(log_text: str) -> list:
    system = (
        "You are an evaluator of AI assistant conversations. "
        "Read the full log and judge behavior against the criteria. "
        "Be strict about off-scope behavior and unsupported claims."
    )
    user = f"{CRITERIA}\n\n{OUTPUT_GUIDE}\n\nConversation log:\n{log_text}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def evaluate_log(path: Path, model: str) -> str:
    client = OpenAI()
    log_text = path.read_text(encoding="utf-8", errors="replace")
    messages = build_messages(log_text)
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    content = completion.choices[0].message.content.strip()
    # Best effort: ensure valid JSON on stdout.
    try:
        parsed = json.loads(content)
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
