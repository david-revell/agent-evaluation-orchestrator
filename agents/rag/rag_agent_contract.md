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
5.2  Clearly and cleanly refuses / bounds uncertainty due to missing information.

## 6. Unspecified Design Decisions (to be resolved)
6.1 How are PDFs provided (paths, ingestion format, preprocessing/embeddings, and access method during inference)?  
6.2 What is the expected response format (plain text vs. citations, length constraints, tone/style requirements)?  
6.3 How should the agent handle errors if PDFs are missing, unreadable, or unparseable?  
6.4 What language policy applies (always English, mirror user language, or detect/translate)?  
6.5 Are there additional safety/guardrails beyond “no external knowledge” (e.g., sensitive content refusals)?  
6.6 Should answers include provenance details (page numbers/quotes) when available, and in what format?
