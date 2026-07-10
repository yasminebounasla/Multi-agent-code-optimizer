"""
Simple Groq API wrapper shared by all agents.
Set your API key as an environment variable: GROQ_API_KEY
"""

import os
import json
import re
from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # reads .env in the project root, if present, and sets env vars from it

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


def _fix_triple_quoted_strings(raw: str) -> str:
    """
    Sometimes the LLM writes Python-style triple-quoted strings inside the
    JSON instead of a properly escaped JSON string. Standard JSON doesn't
    support triple quotes, which breaks parsing. This finds any such block
    and re-encodes its content as a valid JSON string (proper escaping).
    """
    pattern = re.compile(r'"""(.*?)"""', re.DOTALL)

    def _replacer(match):
        content = match.group(1)
        return json.dumps(content)  # produces a correctly escaped JSON string, quotes included

    return pattern.sub(_replacer, raw)


def ask_llm_json(system_prompt: str, user_prompt: str) -> dict:
    """Same as ask_llm but parses the result as JSON. Raises if parsing fails."""
    raw = ask_llm(system_prompt, user_prompt, expect_json=True)

    try:
        return json.loads(raw, strict=False)
    except json.JSONDecodeError:
        pass  # try the repair step below before giving up

    try:
        repaired = _fix_triple_quoted_strings(raw)
        return json.loads(repaired, strict=False)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON:\n{raw}") from e