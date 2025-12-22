"""
Script: rag_runner.py
Version: v1

Single-turn RAG runner that writes logs in the same format as the calendar runner.
"""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent
RAG_DIR = ROOT_DIR / "agents" / "rag"
SCENARIOS_CSV = RAG_DIR / "rag_scenarios.csv"
DEFAULT_MAX_TURNS = 1

# Allow the RAG module to be imported without colliding with the installed `agents` package.
sys.path.insert(0, str(RAG_DIR))
import rag_agent  # type: ignore  # noqa: E402

USE_HUMAN_INPUT = (os.getenv("RAG_HUMAN_USER") or os.getenv("HUMAN_USER") or "0") == "1"


def load_scenarios(csv_path: Path) -> List[Dict[str, str]]:
    if not csv_path.exists():
        return []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, str]] = []
        for row in reader:
            scenario = (row.get("scenario") or "").strip()
            question = (
                row.get("question")
                or row.get("initial_user_message")
                or ""
            ).strip()
            if scenario and question:
                rows.append({"scenario": scenario, "question": question})
        return rows


def choose_scenario(scenarios: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    if not scenarios:
        return None
    desired = os.getenv("RAG_SCENARIO_NAME")
    if not desired:
        return scenarios[0]
    for row in scenarios:
        if row.get("scenario") == desired:
            return row
    return scenarios[0]


def read_question_from_args() -> str:
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:]).strip()
    return ""


def save_history(conversation_history: List[Dict[str, str]], run_metadata: Dict[str, str]) -> None:
    os.makedirs("conversation_logs", exist_ok=True)
    history_string = "Run metadata:\n"
    for key, value in run_metadata.items():
        history_string += f"- {key}: {value}\n"
    history_string += "\nConversation:\n\n"
    for turn in conversation_history:
        history_string += f" - {turn['role']} [{turn['timestamp']}]:\n {turn['content']}\n"

    filename = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.txt"
    path = os.path.join("conversation_logs", filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(history_string)


def main() -> None:
    print("\n=== RAG Agent Runner ===")

    cli_question = read_question_from_args()
    scenario = ""
    mode = ""
    question = ""

    if cli_question:
        question = cli_question
        scenario = "cli_question"
        mode = "cli"
    elif USE_HUMAN_INPUT:
        mode = "human"
        scenario = "human_input"
        question = input("You: ").strip()
    else:
        mode = "synthetic"
        scenarios = load_scenarios(SCENARIOS_CSV)
        scenario_row = choose_scenario(scenarios)
        if not scenario_row:
            print(f"No scenarios found in {SCENARIOS_CSV}. Add rows with scenario and question.")
            return
        scenario = scenario_row["scenario"]
        question = scenario_row["question"]

    if not question:
        print("No question provided; exiting.")
        return

    session_id = f"rag_run_{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    max_turns = str(DEFAULT_MAX_TURNS)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    answer = rag_agent.answer_question(question)

    conversation_history = [
        {"role": "user", "content": question, "timestamp": timestamp},
        {"role": "assistant", "content": answer, "timestamp": timestamp},
    ]

    run_metadata = {
        "session_id": session_id,
        "mode": mode,
        "scenario": scenario,
        "max_turns": max_turns,
        "stop_reason": "single_turn",
    }

    save_history(conversation_history, run_metadata)
    print(answer)


if __name__ == "__main__":
    main()
