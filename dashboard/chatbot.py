import json
import os
from typing import Any

from groq import Groq
import streamlit as st
from groq.types.chat import ChatCompletionMessageParam


SYSTEM_PROMPT = """You are Harvest-IQ, a careful agricultural decision-support assistant.

Answer the user's question using only the supplied Harvest-IQ forecast context and
conversation. Do not invent yield, weather, price, profit, or recommendation values.
The market value is a relative price index, not a rupee price. Explain uncertainty,
fallbacks, and failed stages when they appear in the context. Give practical,
easy-to-understand advice, but remind the user to confirm decisions with local
weather, soil, mandi prices, and an agriculture expert when appropriate.
"""


def _client() -> Groq:
    api_key = os.getenv("GROQ_API")
    if not api_key:
        try:
            api_key = st.secrets["GROQ_API"]
        except (FileNotFoundError, KeyError):
            api_key = None
    if not api_key:
        raise RuntimeError(
            "GROQ_API is not configured. Add it to .env locally or Streamlit secrets."
        )
    return Groq(api_key=api_key)


def answer_question(
    question: str,
    forecast: dict[str, Any],
    history: list[ChatCompletionMessageParam],
    model: str = "allam-2-7b",
) -> str:
    """Return a response grounded in the latest forecast result."""
    context = json.dumps(forecast, ensure_ascii=False, indent=2)
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    messages.extend(history[-10:])
    messages.append(
        {
            "role": "user",
            "content": (
                f"Latest Harvest-IQ forecast context:\n```json\n{context}\n```\n\n"
                f"User question:\n{question}"
            ),
        }
    )

    response = _client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=700,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Groq returned an empty response.")
    return content.strip()
