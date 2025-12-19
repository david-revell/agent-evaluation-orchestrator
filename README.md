# Agent Evaluation Orchestrator

Run conversations against an AI agent, save the resulting logs, and evaluate those logs after the fact.

This repo currently uses a Google Calendar MCP agent as a stand-in “agent under test”, but the goal is that the evaluation layer works for other agents later.

## What it does

1. Runs a conversation in one of two modes:
   - synthetic user (driven by `scenarios.csv`)
   - human user (terminal input)
2. Saves a plain-text conversation log to `conversation_logs/`
3. Evaluates one or more saved logs with an LLM in a single batch, producing per-log verdicts plus a batch summary, and writes the JSON to `evaluation_logs/`

## Bias / fairness note

- Logs can contain run metadata (scenario name, max turns, mode) for repeatability.
- The evaluator strips metadata and evaluates conversation content only.
- Log filenames are neutral (they do not include scenario names) to reduce information leakage.

## Key files

- `mcp_calendar_agent.py`: runs conversations (synthetic or human), writes logs
- `scenarios.csv`: synthetic user scenarios
- `conversation_logs/`: saved transcripts
- `evaluation_logs/`: saved evaluation outputs (per batch)
- `evaluate_log.py`: evaluates one or more log files in a single batch and writes JSON to `evaluation_logs/`
- `project_charter.md`: project goals and boundaries

## How to run

1. Set your OpenAI API key (and anything else your environment needs).

2. Run in human mode (blocking terminal input) — PowerShell:
   ```powershell
   $env:HUMAN_USER=1; python mcp_calendar_agent.py
   ```
   Stop by entering an empty line or `/quit`.

3. Run in synthetic mode (scenario-driven) — PowerShell:
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

## Status

Early-stage. The focus is on making runs repeatable, comparable, and inspectable via logs.
