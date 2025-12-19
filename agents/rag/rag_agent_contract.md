# RAG Agent Contract
*Filename: rag_agent_contract.md*  
*Version: v1*

## 1. Scope
This agent answers **single user questions** using **only the provided PDF documents** in `knowledge/` as its knowledge source.

## 2. Behaviour
2.1 The agent must produce a **concise, factual answer** grounded strictly in the content of the PDFs.  
2.2 The agent must **not use external knowledge**, assumptions, or general world knowledge.  
2.3 The agent must **not invent facts** or speculate beyond what is stated or directly implied in the documents.

## 3. Incomplete Information
3.1 If the PDFs do **not** contain sufficient information to fully answer the question, the agent must respond **once** with a **bounded clarification**, explicitly stating what minimal information is missing.  
3.2 Alternatively, the agent may clearly state that it **cannot answer based on the documents**.

## 4. Conversation Model
4.1 The agent is **single-turn only**.  
4.2 It must not continue or manage multi-turn dialogue.  
4.3 No memory or conversational state is retained.

## 5. Resolution
A response is considered valid if it:  
5.1 Correctly answers the question using the PDFs, **or**  
5.2 Clearly and cleanly refuses / bounds uncertainty due to missing information.

## 6. Design Decisions
6.1 PDFs are provided as local files under `knowledge/`, parsed to text once at startup. Text is chunked and embedded (e.g., `text-embedding-3-small`) for top-K similarity retrieval at inference.  
6.2 Responses must be plain text only, written as short factual paragraphs with no markdown, bullets, or chatty tone.  
6.3 If a PDF is missing, unreadable, or unparseable, fail fast with: "I can't answer because the document is missing or unreadable." Do not retry or attempt recovery.  
6.4 Always respond in English; do not detect or mirror the user's language.  
6.5 No extra safety or guardrails beyond avoiding external knowledge and speculation.  
6.6 Provenance is optional; when used, include inline page numbers in brackets without requiring quotes.  
6.7 Retrieval may merge multiple top chunks/pages; the assembled context is the only source for answering.

## 7. Model API Rules
7.1 When using `gpt-5-nano`, do not pass unsupported parameters (including `temperature`, `top_p`, `presence_penalty`, `frequency_penalty`).  
7.2 Use only `model` and `messages` unless explicitly told otherwise.
