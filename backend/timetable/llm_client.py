# backend/llm_client.py
import os
import json
import time
import logging

import requests # pyright: ignore[reportMissingModuleSource]

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")
OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # change if you want another model
DEFAULT_TIMEOUT = 30

if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set — llm_client will fail until set.")


def ask_llm(prompt: str, max_tokens: int = 1024, temperature: float = 0.2, retries: int = 2) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured in environment")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant specialized in timetable optimization."},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "n": 1,
    }

    for attempt in range(retries + 1):
        try:
            resp = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            # OpenAI-style response structure: choices[0].message.content
            content = None
            if "choices" in data and len(data["choices"]) > 0 and "message" in data["choices"][0]:
                content = data["choices"][0]["message"].get("content")
            elif "choices" in data and len(data["choices"]) > 0 and "text" in data["choices"][0]:
                content = data["choices"][0]["text"]
            else:
                # fallback: try to return full JSON as pretty string
                content = json.dumps(data)
            return content
        except requests.RequestException as exc:
            logger.exception("LLM request failed (attempt %s): %s", attempt + 1, exc)
            if attempt < retries:
                time.sleep(1 + attempt * 2)
                continue
            raise
