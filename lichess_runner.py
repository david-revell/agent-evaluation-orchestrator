"""
Script: lichess_runner.py
Version: v1

Multi-turn Lichess runner that writes logs in the same format as the calendar runner.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openai import OpenAI
from dotenv import load_dotenv
from agents import Runner
from agents.memory.sqlite_session import SQLiteSession

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv()
LICHESS_DIR = ROOT_DIR / "agents" / "lichess"
SCENARIOS_CSV = LICHESS_DIR / "lichess_scenarios.csv"
DEFAULT_MAX_TURNS = 10

# Allow the Lichess module to be imported without colliding with the installed `agents` package.
sys.path.insert(0, str(LICHESS_DIR))
import lichess_agent  # type: ignore  # noqa: E402

SIMULATED_USER_MODEL = os.getenv("LICHESS_SIMULATED_USER_MODEL") or os.getenv("SIMULATED_USER_MODEL") or "gpt-5-nano"
_human_flag = os.getenv("LICHESS_HUMAN_USER") or os.getenv("HUMAN_USER") or "0"
USE_HUMAN_INPUT = _human_flag == "1"

client = OpenAI() if not USE_HUMAN_INPUT else None


def load_scenarios(csv_path: Path) -> List[Dict[str, str]]:
    if not csv_path.exists():
        return []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row.get("scenario") and row.get("initial_user_message")]


def format_history(history: List[Dict[str, str]]) -> str:
    lines = []
    for turn in history:
        role = turn.get("role", "")
        content = turn.get("content", "").strip()
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def simulate_user_turn(
    scenario: str,
    last_agent_reply: str,
    conversation_history: List[Dict[str, str]],
) -> Tuple[str, bool, Optional[str]]:
    system_prompt = (
        "You simulate the user in a conversation with a Lichess assistant. "
        "Stay consistent with the scenario. Always add new information to progress the task. "
        "Do not ask the assistant questions. Do not repeat or paraphrase the assistant. "
        "If the task is done or blocked, set continue to false and include a short reason."
    )

    history_text = format_history(conversation_history)
    user_prompt = (
        "Respond with JSON: {\"message\": \"<next user message>\", \"continue\": true|false, "
        "\"reason\": \"<optional stop reason when continue is false>\"}.\n"
        f"Scenario: {scenario}\n"
        f"Agent reply: {last_agent_reply}\n"
        f"Conversation so far:\n{history_text}"
    )

    if client is None:
        return "No further actions.", False, "Simulator disabled in human mode."

    completion = client.chat.completions.create(
        model=SIMULATED_USER_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = completion.choices[0].message.content.strip()
    try:
        parsed = json.loads(raw)
        msg = parsed.get("message", "").strip()
        cont = bool(parsed.get("continue", True))
        reason = parsed.get("reason")

        if not msg:
            msg = reason or "No further actions."
        elif last_agent_reply and msg.lower() == last_agent_reply.strip().lower():
            msg = reason or "No further actions."

        return msg, cont, reason
    except Exception:
        return raw, True, None


def choose_scenario(scenarios: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    if not scenarios:
        return None
    desired = os.getenv("LICHESS_SCENARIO_NAME")
    if not desired:
        return scenarios[0]
    for row in scenarios:
        if row.get("scenario") == desired:
            return row
    return scenarios[0]


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


def run_turn_logic(user_input: str, session: SQLiteSession):
    return Runner.run_sync(lichess_agent.lichess_agent, user_input, session=session)


def main() -> None:
    print("\n=== Lichess Agent Runner ===")
    print("Welcome to the Lichess API chat. Type 'help' for capabilities.")
    mode_label = "Human input (stdin)" if USE_HUMAN_INPUT else "LLM-simulated user"
    print(f"Mode: {mode_label}")

    if USE_HUMAN_INPUT:
        scenario = "human_input"
        print("Type your message each turn. Enter empty input or /quit to stop.")
        user_input = input("You: ")
        if user_input.strip().lower() in {"help", "?", "/help"}:
            print(lichess_agent.help_text())
            user_input = input("You: ")
        if not user_input.strip():
            print("No input provided; exiting.")
            return
    else:
        scenarios = load_scenarios(SCENARIOS_CSV)
        scenario_row = choose_scenario(scenarios)
        if not scenario_row:
            print(f"No scenarios found in {SCENARIOS_CSV}. Add rows with scenario and initial_user_message.")
            return
        scenario = scenario_row["scenario"]
        user_input = scenario_row["initial_user_message"]

    max_turns = int(os.getenv("MAX_TURNS", DEFAULT_MAX_TURNS))
    session_id = f"lichess_repl_{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    print(f"Scenario: {scenario} | Session: {session_id}")
    session = SQLiteSession(session_id=session_id, db_path="chat_history.db")

    turn = 0
    conversation_history: List[Dict[str, str]] = []
    next_user_input: Optional[str] = user_input
    final_turn = False
    stop_reason: Optional[str] = None

    try:
        while turn < max_turns and next_user_input is not None:
            user_input = next_user_input
            turn += 1

            print(f"\n=== User input (turn {turn}) ===")
            print(user_input)

            result = run_turn_logic(user_input, session=session)
            agent_reply = str(result.final_output) if hasattr(result, "final_output") else str(result)

            print(f"\n=== Agent final_output (turn {turn}) ===")
            print(agent_reply)

            conversation_history.append(
                {
                    "role": "user",
                    "content": user_input,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            conversation_history.append(
                {
                    "role": "assistant",
                    "content": agent_reply,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

            if final_turn:
                break
            if turn >= max_turns:
                stop_reason = stop_reason or f"Reached max turns ({max_turns})"
                print(f"Reached max turns ({max_turns}); stopping.")
                break

            if USE_HUMAN_INPUT:
                next_user_input = input("\nYou: ")
                if next_user_input.strip().lower() in {"help", "?", "/help"}:
                    print(lichess_agent.help_text())
                    next_user_input = input("\nYou: ")
                if not next_user_input.strip() or next_user_input.strip().lower() in {"/quit", "quit", "exit"}:
                    stop_reason = stop_reason or "User ended session."
                    break
            else:
                user_input, continue_flag, reason = simulate_user_turn(
                    scenario=scenario,
                    last_agent_reply=agent_reply,
                    conversation_history=conversation_history,
                )
                next_user_input = user_input
                if not continue_flag:
                    final_turn = True
                    stop_reason = reason
    finally:
        close_fn = getattr(session, "close", None)
        run_metadata = {
            "session_id": session_id,
            "mode": "human" if USE_HUMAN_INPUT else "synthetic",
            "scenario": scenario,
            "max_turns": str(max_turns),
            "stop_reason": stop_reason or "",
        }
        save_history(conversation_history, run_metadata)
        if callable(close_fn):
            close_fn()


if __name__ == "__main__":
    main()
