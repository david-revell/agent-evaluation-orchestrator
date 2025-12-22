# RAG Agent (Minimal)

This directory contains a **minimal, single-turn RAG agent** used as an *agent under test* for Phase 5.1 of the Agent Evaluation Orchestrator.

The agent answers questions **only from the documents in `knowledge/`** and follows the behaviour defined in `rag_agent_contract.md`.

This is **not** a production chatbot and is intentionally limited in scope.

RAG runs are executed via `rag_runner.py` at the repo root. Synthetic questions live in `rag_scenarios.csv`, and the runner writes standard logs to `conversation_logs/` so `evaluate_log.py` can be used without changes.