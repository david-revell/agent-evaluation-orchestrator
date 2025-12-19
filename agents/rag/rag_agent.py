"""
Script: rag_agent.py
Version: v1

Minimal RAG Agent 

This module defines a minimal, single-turn Retrieval-Augmented Generation (RAG) agent
used as an agent under test for the Agent Evaluation Orchestrator.

Selection:
- This agent is selected when the environment variable AGENT=rag.

Behaviour:
- Behaviour is defined entirely by `rag_agent_contract.md`.
- Knowledge source is limited to the PDFs in `knowledge/`.

This file intentionally contains no implementation yet.
"""
