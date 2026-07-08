"""
Simple Groq API wrapper shared by all agents.
Set your API key as an environment variable: GROQ_API_KEY
"""

import os
import json
from groq import Groq

MODEL = "llama-3.3-70b-versatile"

_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def ask_llm(system_prompt: str, user_prompt: str, expect_json: bool = False) -> str:
    """
    Send a single-turn prompt to the LLM and return the raw text response.
    If expect_json=True, we instruct the model to return ONLY JSON and
    strip markdown fences if it adds them anyway.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = _client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.2,
    )

    text = response.choices[0].message.content.strip()

    if expect_json:
        text = text.replace("```json", "").replace("```", "").strip()

    return text


def ask_llm_json(system_prompt: str, user_prompt: str) -> dict:
    """Same as ask_llm but parses the result as JSON. Raises if parsing fails."""
    raw = ask_llm(system_prompt, user_prompt, expect_json=True)
    try:
        return json.loads(raw, strict=False)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON:\n{raw}") from e