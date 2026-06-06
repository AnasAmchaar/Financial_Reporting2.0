"""AI routes with RAG-enhanced financial data grounding."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    context: dict | str | None = None
    use_rag: bool = True


@router.post("/ai/chat")
async def chat_with_ai(request: ChatRequest):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not set in the environment variables. Please set it to use the AI Chatbot.",
        )

    try:
        if request.use_rag:
            # RAG-enhanced path: retrieve relevant data from vector store
            from ecoeye2.server.rag.retriever import rag_generate

            response_text = rag_generate(
                user_message=request.message,
                page_context=request.context,
                top_k=8,
                api_key=api_key,
            )
            return {"response": response_text, "mode": "rag"}
        else:
            # Legacy path: direct Gemini call with page context only
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            system_instruction = (
                "You are an expert financial and economic analyst embedded inside the EcoEye2 "
                "Purchasing-Power-Aware Financial Reporting Application. "
                "Your job is to analyze the data and charts provided to you in the context, and answer the user's questions clearly, professionally, and concisely. "
                "When analyzing data, highlight key trends, anomalies, and the true economic profit or purchasing power impacts. "
                "Use Markdown formatting for your responses. Keep responses brief but insightful."
            )

            prompt = f"User Message:\n{request.message}\n\n"
            if request.context:
                prompt += f"Application Context (Current Data/Charts on Screen):\n{request.context}\n"

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                ),
            )
            return {"response": response.text, "mode": "direct"}

    except Exception as e:
        logger.error(f"Failed to generate AI response: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to communicate with AI provider: {str(e)}",
        )


@router.post("/ai/rag/reindex")
async def rag_reindex():
    """Trigger a full re-index of the RAG vector store."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not set.",
        )

    try:
        from ecoeye2.server.rag.indexer import build_index

        result = build_index(api_key=api_key)
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("detail", "Indexing failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("RAG reindex failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Re-index failed: {str(e)}")


@router.get("/ai/rag/status")
async def rag_status():
    """Return the current health of the RAG vector store."""
    try:
        from ecoeye2.server.rag.indexer import get_index_status

        return get_index_status()
    except Exception as e:
        logger.error("RAG status check failed: %s", e)
        return {"status": "error", "detail": str(e)}
