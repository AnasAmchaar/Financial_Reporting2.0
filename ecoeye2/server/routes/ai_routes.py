from __future__ import annotations

import os
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    context: dict | str | None = None

@router.post("/ai/chat")
async def chat_with_ai(request: ChatRequest):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=500, 
            detail="GEMINI_API_KEY is not set in the environment variables. Please set it to use the AI Chatbot."
        )

    genai.configure(api_key=api_key)
    
    # Use Gemini 2.5 Flash as it is fast and excellent for data analysis
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=(
            "You are an expert financial and economic analyst embedded inside the EcoEye2 "
            "Purchasing-Power-Aware Financial Reporting Application. "
            "Your job is to analyze the data and charts provided to you in the context, and answer the user's questions clearly, professionally, and concisely. "
            "When analyzing data, highlight key trends, anomalies, and the true economic profit or purchasing power impacts. "
            "Use Markdown formatting for your responses. Keep responses brief but insightful."
        )
    )

    prompt = f"User Message:\n{request.message}\n\n"
    if request.context:
        prompt += f"Application Context (Current Data/Charts on Screen):\n{request.context}\n"

    try:
        response = model.generate_content(
            prompt,
            safety_settings={
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        return {"response": response.text}
    except Exception as e:
        logger.error(f"Failed to generate AI response: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to communicate with AI provider: {str(e)}")
