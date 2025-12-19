"""
Script: evaluate_log.py
Version: v3

Purpose:
Read one or more saved conversation logs, ask an LLM to produce per-log evaluations,
and emit a batch summary in the same run.

Usage:
  python evaluate_log.py path/to/log1.txt [path/to/log2.txt ...]
Env:
  EVALUATOR_MODEL (default: gpt-5-nano)
"""

import json
import sys
import os
from datetime import datetime
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

# Output format guidance for batch evaluation.
BATCH_OUTPUT_GUIDE = """Return JSON only:
{
  "summary": {
    "total": <int>,
    "verdict_counts": {"pass": <int>, "warn": <int>, "fail": <int>, "error": <int>},
    "most_common_bad_findings": [
      {"text": "short finding", "count": <int>},
      ...
    ]
  },
  "per_log": [
    {
      "log_id": "L1",
      "verdict": "pass" | "warn" | "fail" | "error",
      "findings": [
        {"text": "short finding", "evaluation": "good" | "bad" | "neutral"},
        ...
      ]
    },
    ...
  ]
}
Rules:
- Use 'fail' for clear violations, 'warn' for minor issues/uncertainty, 'pass' when no material issues are found.
- If you cannot produce structured output for a log, mark its verdict as 'error' and include a short bad finding.
- Each finding MUST include an 'evaluation' label: good (appropriate behavior), bad (inappropriate), neutral (observation/ambiguous/user-caused).
- The summary must be derived from the per_log results (counts and most frequent bad finding texts)."""


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


def build_messages(batch_text: str) -> list:
    system = (
        "You are an evaluator of AI assistant conversations. "
        "Read all provided logs in this batch and judge behavior against the criteria. "
        "Be strict about off-scope behavior and unsupported claims. "
        "Do not penalize internal-only fields found in logs (e.g., 'reasoning' JSON fields) "
        "unless the assistant exposed them to the user as user-facing text. "
        "Produce both per-log results and a batch summary in one response."
    )
    user = f"{CRITERIA}\n\n{BATCH_OUTPUT_GUIDE}\n\nConversation logs:\n{batch_text}"
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


def evaluate_batch(paths: list[Path], model: str) -> dict:
    """
    Evaluate all logs in a single LLM call; batch size = 1 is the degenerate case.
    """
    client = OpenAI()
    parts = []
    for idx, path in enumerate(paths, start=1):
        log_text = path.read_text(encoding="utf-8", errors="replace")
        log_text = conversation_only(log_text)
        parts.append(f"Log {idx} (id: L{idx}):\n{log_text}\n")
    batch_text = "\n".join(parts).strip()
    messages = build_messages(batch_text)
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    content = completion.choices[0].message.content.strip()
    try:
        parsed = json.loads(content)
        # Normalize findings for each log if present.
        per_log = parsed.get("per_log")
        if isinstance(per_log, list):
            normalized = []
            for item in per_log:
                if isinstance(item, dict):
                    findings = normalize_evaluation_result(item).get("findings")
                    item["findings"] = findings if findings is not None else []
                    normalized.append(item)
            parsed["per_log"] = normalized
        return parsed
    except Exception:
        # If parsing fails, return a minimal error structure.
        return {
            "summary": {
                "total": len(paths),
                "verdict_counts": {"error": len(paths)},
                "most_common_bad_findings": [
                    {"text": "Evaluator returned non-JSON output.", "count": 1}
                ],
            },
            "per_log": [
                {
                    "log_id": f"L{idx}",
                    "verdict": "error",
                    "findings": [
                        {
                            "text": "Evaluator returned non-JSON output.",
                            "evaluation": "bad",
                        }
                    ],
                    "raw": content,
                }
                for idx in range(1, len(paths) + 1)
            ],
        }


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python evaluate_log.py path/to/log1.txt [path/to/log2.txt ...]")
        sys.exit(1)

    model = os.getenv("EVALUATOR_MODEL", "gpt-5-nano")
    paths = [Path(p) for p in sys.argv[1:]]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print("Log file(s) not found: " + ", ".join(missing))
        sys.exit(1)

    batch_result = evaluate_batch(paths, model=model)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path.cwd() / "evaluation_logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"batch_evaluation_{ts}.json"
    out_path.write_text(json.dumps(batch_result, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Evaluation complete: wrote results to {out_path}")


if __name__ == "__main__":
    main()
