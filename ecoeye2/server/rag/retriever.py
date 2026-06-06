"""
RAG Retriever for EcoEye2.

Given a user question, embeds it, performs a semantic search against the
ChromaDB vector index, and constructs a grounded prompt for the LLM.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from google import genai
from google.genai import types

from ecoeye2.server.rag.indexer import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


def _embed_query(text: str, api_key: str) -> list[float]:
    """Embed a single query for retrieval."""
    client = genai.Client(api_key=api_key)
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )
    return result.embeddings[0].values


def retrieve_chunks(
    query: str,
    top_k: int = 8,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve the top-K most relevant chunks from the vector store.

    Returns a list of dicts with keys: ``document``, ``metadata``, ``distance``.
    """
    import chromadb

    api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.warning("No GEMINI_API_KEY for RAG retrieval")
        return []

    if not CHROMA_DIR.exists():
        logger.warning("ChromaDB directory does not exist; run re-index first")
        return []

    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as e:
        logger.warning("Could not load ChromaDB collection: %s", e)
        return []

    if collection.count() == 0:
        logger.warning("ChromaDB collection is empty; run re-index first")
        return []

    # Embed the query
    try:
        query_embedding = _embed_query(query, api_key)
    except Exception as e:
        logger.error("Failed to embed query: %s", e)
        return []

    # Search
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            chunks.append(
                {
                    "document": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                }
            )

    return chunks


def rag_generate(
    user_message: str,
    page_context: str | dict | None = None,
    top_k: int = 8,
    api_key: str | None = None,
) -> str:
    """
    Full RAG pipeline: retrieve relevant chunks, then generate a grounded
    response via Gemini.
    """
    api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return "Error: GEMINI_API_KEY is not configured."

    client = genai.Client(api_key=api_key)

    # 1. Retrieve relevant data chunks
    chunks = retrieve_chunks(user_message, top_k=top_k, api_key=api_key)

    # 2. Build grounded context
    if chunks:
        chunk_texts = "\n\n".join(
            [f"[Source: {c['metadata'].get('type', 'unknown')}] {c['document']}" for c in chunks]
        )
        data_context = (
            "## Retrieved Financial Data (from EcoEye2 database)\n"
            "The following data was retrieved from the company's actual financial records. "
            "Use this data to ground your answer with specific numbers and facts.\n\n"
            f"{chunk_texts}"
        )
    else:
        data_context = (
            "Note: The RAG index has not been built yet or no relevant data was found. "
            "Answer based on general financial knowledge and any page context provided."
        )

    # 3. Build system prompt
    system_instruction = (
        "You are an expert financial and economic analyst embedded inside the EcoEye2 "
        "Purchasing-Power-Aware Financial Reporting Application.\n\n"
        "CRITICAL RULES:\n"
        "1. You MUST answer based on the retrieved financial data provided below. "
        "Cite specific numbers, dates, and metrics from the data.\n"
        "2. If the data doesn't contain enough information to fully answer, "
        "clearly state what is missing and what you can infer.\n"
        "3. Never invent or hallucinate financial figures. If a number comes from the data, "
        "reference it. If it's an estimate, label it as such.\n"
        "4. Highlight key trends, anomalies, purchasing power impacts, and CPI/PPI effects.\n"
        "5. Use Markdown formatting. Keep responses professional, concise, and insightful.\n"
        "6. When discussing inflation, distinguish between nominal and real values."
    )

    # 4. Build prompt
    prompt_parts = [f"## User Question\n{user_message}\n"]
    prompt_parts.append(f"\n{data_context}\n")

    if page_context:
        ctx_str = str(page_context) if not isinstance(page_context, str) else page_context
        prompt_parts.append(
            f"\n## Current Application Context\n{ctx_str}\n"
        )

    prompt = "\n".join(prompt_parts)

    # 5. Generate with Gemini
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
            ),
        )
        return response.text
    except Exception as e:
        logger.error("RAG generation failed: %s", e)
        return f"Error generating response: {str(e)}"
