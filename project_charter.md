# Project Charter
**Agent Evaluation Orchestrator**  
*project_charter.md*  
*version: v3*

---

## 1. Purpose

1.1 The purpose of this project is to build a **generic system for evaluating AI agent behaviour**.

1.2 The system is intended to:

1.2.1 run conversations against an AI agent  
1.2.2 support either a synthetic user or a human as the message source  
1.2.3 capture completed conversations as logs  
1.2.4 evaluate completed conversation logs using an LLM  
1.2.5 produce concise, structured judgements of agent behaviour  

1.3 The project is **not** focused on building or improving an AI agent itself.

1.4 The Google Calendar agent is used solely as a **stand-in target** during development.

1.5 The long-term intent is for the evaluation layer to work with **any AI agent**, including agents accessed via external APIs (for example RAG-based systems), without requiring redesign.

## 2. Boundaries

2.1 This project is deliberately limited to **post-hoc evaluation of completed conversations**.

2.2 The system does not attempt to:

2.2.1 influence or steer agent behaviour during a live conversation  
2.2.2 optimise, fine-tune, or correct the agent under test  
2.2.3 provide a hosted service or interactive user interface at this stage  

2.3 All evaluation is performed **after the fact**, using conversation logs as the sole input.

2.4 These boundaries exist to keep the system simple, inspectable, and reusable across different agents and environments.

## 3. Scope

3.1 The current scope of this project provides mechanisms to run conversations against an AI agent.

3.1.1 Conversations may be driven by a synthetic user  
3.1.2 Conversations may be driven by a human via terminal input  

3.2 The current scope captures each completed conversation as a plain-text log.

3.3 THe current scope provides a standalone evaluator that:

3.3.1 accepts one completed conversation log as input  
3.3.2 uses an LLM to assess agent behaviour against defined criteria  
3.3.3 outputs a concise, structured JSON verdict to the terminal  

3.4 The conversation log is the **only contract** between conversation execution and evaluation.

3.5 No assumptions are made about the agent under test beyond the ability to exchange messages.

3.6 To reduce bias and information leakage, evaluation is performed on **conversation content only**.

3.6.1 Run metadata (scenario identifiers, max turns, models, stop reasons) may be recorded for repeatability and inspection  
3.6.2 The evaluator must **not** use or enforce run settings; it only judges the conversation  
3.6.3 Scenario names should not appear in log filenames, and metadata should be excluded/stripped from evaluator input  

3.7 Known evaluator limitation: the evaluator can be wrong in specific cases.

3.7.1 Example: if the user asks “What day is it today?” and the assistant redirects to calendar-only help, the evaluator may incorrectly mark this as a failure.  
3.7.2 Rationale: redirecting to in-scope calendar tasks can be correct behaviour, “reasoning” in logs may be internal/non-user-facing, and a conversation ending early can be caused by user termination rather than assistant failure.  
3.7.3 This limitation is documented so future improvements can reduce false negatives without changing the system boundaries (post-hoc, log-only evaluation).  
3.7.4 Improving evaluator correctness or tuning its judgement logic is explicitly out of scope for the current scope; incorrect or debatable evaluations are expected and documented rather than fixed.

## 4. Ambition, Stretch Goals, and Open Questions

4.1 The long-term ambition of this project is to act as a **generic evaluation layer for AI agents**, independent of agent implementation or deployment model.

4.2 Plausible future extensions include:

4.2.1 driving conversations against external agents via APIs, including production systems  
4.2.2 automating the full loop of conversation execution, log capture, and evaluation  
4.2.3 evaluating multiple conversation logs in batch  
4.2.4 producing aggregate summaries across multiple runs  
4.2.5 comparing evaluations across different agents  
4.2.6 introducing more standardised or comparable scoring schemes while retaining qualitative findings  

4.3 Open questions intentionally left undecided include:

4.3.1 whether evaluation should always remain a standalone script or be optionally invoked by a higher-level runner  
4.3.2 whether evaluation outputs should remain ephemeral or be persisted  
4.3.3 how strict or formal scoring should become, if at all  

4.4 Items in Section 4 are documented to make intent explicit and visible, not to commit to implementation within v1.

## 5. Next steps

5.1 Define the evaluator to operate on batches of conversation logs, with a single conversation treated as the batch size = 1 case.

5.1.1 Input to the evaluator is always a batch: a list of logs. Output should include per-log verdicts and findings, plus a batch-level summary (counts of pass/warn/fail and the most common bad findings) produced in the same run.  
5.1.2 Cross-run behaviour is native to the evaluator: when batch size > 1, the evaluator emits both per-log and aggregated results; no separate cross-run layer consumes evaluator outputs.  
5.1.3 Each log in the batch must expose a minimal, consistent surface so aggregation is meaningful: a plain-language outcome/stop reason; whether key user asks were satisfied or blocked; any tool limits hit (for example, cannot add attendees or set reminders); evidence of changes attempted or made (create/update/delete with times, attendees, locations if touched); conflicts detected and how they were resolved; notable off-scope or empty turns; and the event identifiers or titles referenced when moves or updates were attempted.  
5.1.4 The evaluator should handle the full batch in a single LLM call so it can reason across all logs at once; batch size = 1 is the degenerate case. Per-log judgements and the batch summary come from that shared context rather than post-hoc aggregation.  

5.2 After the summary exists, introduce a second, very different agent (for example a RAG-based agent) to stress-test generalisation.

5.2.1 This is not scope creep into improving the agent under test; it is expanding the variety of agents to validate that the evaluation layer stays generic.  

