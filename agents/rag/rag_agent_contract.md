# RAG Agent Contract
*Filename: rag_agent_contract.md*  
*Version: v1*

## Scope
This agent answers **single user questions** using **only the provided PDF documents** as its knowledge source.

## Behaviour
- The agent must produce a **concise, factual answer** grounded strictly in the content of the PDFs.
- The agent must **not use external knowledge**, assumptions, or general world knowledge.
- The agent must **not invent facts** or speculate beyond what is stated or directly implied in the documents.

## Incomplete Information
- If the PDFs do **not** contain sufficient information to fully answer the question, the agent must respond **once** with a **bounded clarification**, explicitly stating what minimal information is missing.
- Alternatively, the agent may clearly state that it **cannot answer based on the documents**.

## Conversation Model
- The agent is **single-turn only**.
- It must not continue or manage multi-turn dialogue.
- No memory or conversational state is retained.

## Resolution
A response is considered valid if it:
- Correctly answers the question using the PDFs, **or**
- Clearly and cleanly refuses / bounds uncertainty due to missing information.

## Unspecified Design Decisions (to be resolved)
- How are PDFs provided (paths, ingestion format, preprocessing/embeddings, and access method during inference)?
- What is the expected response format (plain text vs. citations, length constraints, tone/style requirements)?
- How should the agent handle errors if PDFs are missing, unreadable, or unparseable?
- What language policy applies (always English, mirror user language, or detect/translate)?
- Are there additional safety/guardrails beyond “no external knowledge” (e.g., sensitive content refusals)?
- Should answers include provenance details (page numbers/quotes) when available, and in what format?
