"""
Script: rag_agent.py
Version: v4

Single-turn RAG agent implementing rag_agent_contract.md with embedding-based retrieval.
"""

from __future__ import annotations

import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from openai import OpenAI
from dotenv import load_dotenv

PDF_ERROR_MESSAGE = "I can't answer because the document is missing or unreadable."
MODEL_NAME = "gpt-5-nano"
EMBED_MODEL = "text-embedding-3-small"
USE_LLM = os.getenv("RAG_USE_LLM", "1") != "0"
DEBUG = os.getenv("RAG_DEBUG", "0") == "1"
TOP_K = 3
MAX_CHARS_PER_CHUNK = 900

load_dotenv()

# Match the calendar agent: rely on OPENAI_API_KEY in the environment.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else OpenAI()

# Prefer pypdf, fall back to PyPDF2 if available.
try:  # pragma: no cover - import resolution
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    try:
        from PyPDF2 import PdfReader  # type: ignore
    except Exception:
        PdfReader = None  # type: ignore


@dataclass
class PageText:
    document: str
    page_number: int
    text: str
    tokens: List[str]


@dataclass
class Chunk:
    document: str
    page_number: int
    text: str
    embedding: List[float]


def fatal_pdf_error() -> None:
    """Fail fast on any PDF access/parsing issue."""
    print(PDF_ERROR_MESSAGE)
    sys.exit(1)


def normalize_text(text: str) -> str:
    # Collapse whitespace to keep downstream scoring simple.
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
    stopwords = {
        "the",
        "and",
        "of",
        "in",
        "to",
        "for",
        "a",
        "an",
        "on",
        "with",
        "at",
        "by",
        "from",
        "is",
        "are",
        "as",
        "that",
        "this",
        "it",
        "be",
        "what",
        "why",
        "how",
        "who",
        "which",
        "when",
        "where",
    }
    return [t for t in tokens if t and t not in stopwords]


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(text: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> List[str]:
    sentences = split_sentences(text)
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    for sentence in sentences:
        if current_len + len(sentence) > max_chars and current:
            chunks.append(" ".join(current).strip())
            current = []
            current_len = 0
        current.append(sentence)
        current_len += len(sentence) + 1
    if current:
        chunks.append(" ".join(current).strip())
    return [c for c in chunks if c]


def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    if not texts:
        return []
    try:
        resp = client.embeddings.create(model=EMBED_MODEL, input=list(texts))
        return [item.embedding for item in resp.data]
    except Exception:
        return []


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def load_documents() -> List[PageText]:
    """Load and parse all PDFs in knowledge/ once at startup."""
    knowledge_dir = Path(__file__).resolve().parent / "knowledge"
    if not knowledge_dir.exists() or not knowledge_dir.is_dir():
        fatal_pdf_error()

    if PdfReader is None:
        fatal_pdf_error()

    pdf_paths = sorted(knowledge_dir.glob("*.pdf"))
    if not pdf_paths:
        fatal_pdf_error()

    pages: List[PageText] = []
    for path in pdf_paths:
        try:
            reader = PdfReader(str(path))
        except Exception:
            fatal_pdf_error()

        try:
            for idx, page in enumerate(reader.pages):
                try:
                    raw_text = page.extract_text() or ""
                except Exception:
                    raw_text = ""
                text = normalize_text(raw_text)
                if text:
                    pages.append(
                        PageText(
                            document=path.name,
                            page_number=idx + 1,
                            text=text,
                            tokens=tokenize(text),
                        )
                    )
        except Exception:
            fatal_pdf_error()

    if not pages:
        fatal_pdf_error()
    return pages


def score_page(tokens: Sequence[str], page: PageText) -> int:
    if not tokens or not page.tokens:
        return 0
    page_token_set = set(page.tokens)
    return sum(1 for t in tokens if t in page_token_set)


def select_sentences(tokens: Sequence[str], text: str, limit_chars: int = 600) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return ""
    lower_tokens = [t.lower() for t in tokens]
    prioritized: List[str] = []
    for sentence in sentences:
        s_lower = sentence.lower()
        if any(t in s_lower for t in lower_tokens):
            prioritized.append(sentence)
    if not prioritized:
        prioritized = sentences[:2]
    combined = " ".join(prioritized)
    if len(combined) > limit_chars:
        combined = combined[:limit_chars].rsplit(" ", 1)[0].strip()
    return combined.strip()


PAGES: List[PageText] = load_documents()
RAW_CHUNKS_TEXT: List[tuple[str, str, int]] = []
for page in PAGES:
    for chunk in chunk_text(page.text):
        RAW_CHUNKS_TEXT.append((page.document, chunk, page.page_number))

CHUNKS: List[Chunk] = []
embeddings = embed_texts([c[1] for c in RAW_CHUNKS_TEXT])
if not embeddings or len(embeddings) != len(RAW_CHUNKS_TEXT):
    # Embeddings failed; keep CHUNKS empty to trigger refusal later.
    CHUNKS = []
else:
    for (doc, text, page_num), emb in zip(RAW_CHUNKS_TEXT, embeddings):
        CHUNKS.append(Chunk(document=doc, page_number=page_num, text=text, embedding=emb))


def generate_answer(question: str, context: str) -> str:
    """
    Single LLM call using only retrieved context; plain text output.
    """
    system_prompt = (
        "You answer a single user question using ONLY the provided context from PDFs. "
        "Respond in English as one short factual paragraph, plain text only (no markdown or bullets). "
        "If the context is insufficient, reply with a concise refusal or a single bounded clarification "
        "about the missing info. Do not use external knowledge or speculate. If you cite, use inline page "
        "numbers in brackets."
    )
    user_prompt = f"Context:\n{context}\n\nQuestion:\n{question}\n\nAnswer:"

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return "I cannot answer based on the documents."


def answer_question(question: str) -> str:
    tokens = tokenize(question)
    if not tokens:
        return "I cannot answer based on the documents."

    if not CHUNKS:
        return "I cannot answer based on the documents."

    q_embed = embed_texts([question])
    if not q_embed:
        return "I cannot answer based on the documents."
    q_vec = q_embed[0]

    scored_chunks = []
    for chunk in CHUNKS:
        sim = cosine(q_vec, chunk.embedding)
        scored_chunks.append((sim, chunk))
    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    top_chunks = [c for score, c in scored_chunks[:TOP_K] if score > 0]
    if not top_chunks:
        return "I cannot answer based on the documents."

    if DEBUG:
        preview = [(round(s, 3), c.document, c.page_number) for s, c in scored_chunks[:TOP_K]]
        print(f"[debug] tokens={tokens}", file=sys.stderr)
        print(f"[debug] top_chunks={preview}", file=sys.stderr)

    context_parts = [f"Document: {c.document}, page {c.page_number}\n{c.text}" for c in top_chunks]
    context = "\n\n".join(context_parts)

    if not USE_LLM:
        if DEBUG:
            print("[debug] LLM disabled; returning snippet only", file=sys.stderr)
        return context

    return generate_answer(question, context)


def read_question_from_args_or_stdin() -> str:
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:]).strip()
    if not sys.stdin.isatty():
        data = sys.stdin.read().strip()
        if data:
            return data
    try:
        return input().strip()
    except EOFError:
        return ""


def main() -> None:
    question = read_question_from_args_or_stdin()
    answer = answer_question(question) if question else "I cannot answer based on the documents."
    try:
        print(answer)
    except UnicodeEncodeError:
        safe = answer.encode("ascii", "backslashreplace").decode()
        print(safe)


if __name__ == "__main__":
    main()
