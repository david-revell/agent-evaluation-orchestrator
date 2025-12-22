# External Agent Integration Contract
*Filename: external_agent_contract.md*
*Version: v1*

## 1. Purpose and scope
This contract defines the minimum requirements an external agent must meet to plug into the run -> log -> evaluate pipeline. It does **not** specify how the agent is built, only how it is run and logged.

## 2. Supported interaction model
2.1 The pipeline supports **single-turn** and **multi-turn** agents.
2.2 A single-turn agent must answer exactly one user message and then stop.
2.3 A multi-turn agent must accept a sequence of user messages and return one assistant reply per turn.
2.4 The runner controls when to stop; the agent must not manage conversation termination on its own unless instructed by the runner.

## 3. Required inputs to an agent run
3.1 The runner must be able to provide the agent with:
- A user message (plain text).
- Optional conversation history (list of prior user/assistant turns) for multi-turn agents.
- Optional run settings (model name, max turns, etc.). These settings are for execution only and must not affect evaluation.

3.2 The agent must accept input as plain text; it must not require a UI or proprietary client.

## 4. Required outputs from an agent run
4.1 For each user message, the agent must return a **single assistant reply** as plain text.
4.2 The agent must not emit extra framing (no JSON wrappers, no tool traces) unless the agent is specifically designed to do so.
4.3 If the agent cannot answer, it must return a clear refusal or a bounded clarification.

## 5. Conversation log format and guarantees
5.1 Each run must produce a log file in UTF-8 with the following structure:

Run metadata:
- session_id: <string>
- mode: <string>
- scenario: <string>
- max_turns: <int>
- stop_reason: <string>

Conversation:

 - user [YYYY-MM-DD HH:MM:SS]:
  <user text>
 - assistant [YYYY-MM-DD HH:MM:SS]:
  <assistant text>

5.2 The log **must include** the exact headers `Run metadata:` and `Conversation:`.
5.3 Filenames must be neutral and must **not** include scenario names.
5.4 The evaluator reads only the `Conversation:` section; metadata is retained for repeatability but must not be relied on for scoring.

## 6. Error and failure representation
6.1 If the agent fails to produce a reply, the runner must still write a log.
6.2 In failure cases, the assistant turn should contain a short error message (plain text) and the run metadata should include a meaningful `stop_reason` (for example, `agent_error`, `timeout`, or `missing_input`).
6.3 Errors must not break the log format; the evaluator expects valid structure even on failures.

## 7. Compatibility rules (what must not change)
7.1 The log format in Section 5 is the contract between run and evaluation and must not change without updating the evaluator.
7.2 The `Conversation:` block must use the `role [timestamp]` format shown above.
7.3 The evaluator is log-only; it must not require access to tools, agent internals, or external services.

## 8. Quick checklist (minimum to plug in)
8.1 Runner can accept a user message and return one assistant reply.
8.2 Runner writes a UTF-8 log with `Run metadata:` and `Conversation:` blocks.
8.3 Log filenames are neutral (no scenario names).
8.4 Evaluator can read the log without any extra context or services.

## 9. Example log snippet (single-turn)
Run metadata:
- session_id: example_20251222T120000
- mode: synthetic
- scenario: example_scenario
- max_turns: 1
- stop_reason: single_turn

Conversation:

 - user [2025-12-22 12:00:00]:
  What does the document say about nurse licensing in Spain?
 - assistant [2025-12-22 12:00:01]:
  The document explains the licensing steps and required credentials for nurses in Spain, including recognition and registration requirements.

## 10. Non-goals and out-of-scope behaviour
10.1 This contract does **not** require a specific model, tool usage, or retrieval method.
10.2 It does **not** define how agents should be evaluated; it only defines how runs are logged.
10.3 It does **not** require real-time steering, intervention, or interactive UI support.
10.4 It does **not** require storage of tool calls, traces, or hidden reasoning.
