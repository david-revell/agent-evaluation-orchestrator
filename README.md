# Agent Evaluation Orchestrator

Run conversations against multiple AI agents, save the resulting logs, and evaluate those logs after the fact.

This repo focuses on the evaluation pipeline itself, not any single agent. It includes more than one agent under test to demonstrate that the run -> log -> evaluate flow is generic.

## What it does

1. Runs a conversation in one of two modes:
   - synthetic user (driven by `scenarios.csv`)
   - human user (terminal input)
2. Saves a plain-text conversation log to `conversation_logs/`
3. Evaluates one or more saved logs with an LLM in a single batch, producing per-log verdicts plus a batch summary, and writes the JSON to `evaluation_logs/`

Agents under test (examples):
- Google Calendar MCP agent (multi-turn, tool-using)
- Minimal RAG agent (single-turn, document-grounded)
- Lichess agent (multi-turn, API-backed)

## Bias / fairness note

- Logs can contain run metadata (scenario name, max turns, mode) for repeatability.
- The evaluator strips metadata and evaluates conversation content only.
- Log filenames are neutral (they do not include scenario names) to reduce information leakage.

## Key files

- `mcp_calendar_agent.py`: runs conversations (synthetic or human), writes logs
- `scenarios.csv`: synthetic user scenarios
- `rag_runner.py`: runs the RAG agent and writes logs
- `agents/rag/rag_scenarios.csv`: synthetic questions for the RAG agent
- `conversation_logs/`: saved transcripts
- `evaluation_logs/`: saved evaluation outputs (per batch)
- `evaluate_log.py`: evaluates one or more log files in a single batch and writes JSON to `evaluation_logs/`
- `project_charter.md`: project goals and boundaries
- `documentation/external_agent_contract.md`: contract for plugging new agents into the pipeline

## How to run

1. Set your OpenAI API key (and anything else your environment needs).
   This project loads variables from `.env` (if present).

2. Run in human mode (blocking terminal input) - PowerShell:
   ```powershell
   $env:HUMAN_USER=1; python mcp_calendar_agent.py
   ```
   Stop by entering an empty line or `/quit`.

3. Run in synthetic mode (scenario-driven) - PowerShell:
   ```powershell
   $env:HUMAN_USER=0
   $env:SCENARIO_NAME="off_scope_wifi"
   python mcp_calendar_agent.py
   ```
    Optional: `$env:MAX_TURNS=10`.

4. Evaluate one or more saved logs (batch):  
   **Note:** Evaluation output is not guaranteed to be correct. The evaluator can produce false negatives or misinterpret correct agent behaviour. This is a known and documented limitation by design.  
   ```powershell
   python evaluate_log.py conversation_logs\run_YYYYMMDD_HHMMSS_ffffff.txt [more logs...]
   ```
   Example (single log):
   ```powershell
   python evaluate_log.py conversation_logs\run_20251218_125725_516257.txt
   ```
   Example (all logs in a folder, PowerShell):
   ```powershell
   Get-ChildItem conversation_logs\run_*.txt | ForEach-Object { $_.FullName } | % { python evaluate_log.py $_ }
   ```
   By default, the evaluator uses `gpt-5-nano`. Optional: `$env:EVALUATOR_MODEL="gpt-5-nano"`.

   Output:
   - A JSON file is written to `evaluation_logs/` (e.g., `evaluation_logs/batch_evaluation_YYYYMMDD_HHMMSS.json`).
   - The JSON includes a `summary` (counts and common bad findings) and `per_log` entries (verdicts and findings for each log).

Notes:
- `HUMAN_INPUT=1` is supported as a legacy alias for `HUMAN_USER=1`.
- The evaluator remains a separate layer: it reads logs and produces judgements; it does not enforce run settings.


### RAG agent run (single-turn)

RAG scenarios live in `agents/rag/rag_scenarios.csv`.

- Human input (blocking terminal input) - PowerShell:
  ```powershell
  $env:RAG_HUMAN_USER=1; python rag_runner.py
  ```
- Scenario-driven (uses the first row unless RAG_SCENARIO_NAME is set):
  ```powershell
  $env:RAG_SCENARIO_NAME="licensing_overview"
  python rag_runner.py
  ```
- One-off question:
  ```powershell
  python rag_runner.py "Your question here"
  ```

### Lichess agent run (multi-turn)

Lichess scenarios live in `agents/lichess/lichess_scenarios.csv`.

- Human input (blocking terminal input) - PowerShell:
  ```powershell
  $env:LICHESS_HUMAN_USER=1; python lichess_runner.py
  ```
- Scenario-driven (uses the first row unless LICHESS_SCENARIO_NAME is set):
  ```powershell
  $env:LICHESS_SCENARIO_NAME="daily_puzzle"
  python lichess_runner.py
  ```

Notes:
- The Lichess agent is read-only for now (no follow/unfollow, no study edits).
- Tokens default to `LICHESS_TOKEN` and fall back to other Lichess token env vars; see `agents/lichess/README_lichess.md`.

## Status

Early-stage. The focus is on making runs repeatable, comparable, and inspectable via logs.
