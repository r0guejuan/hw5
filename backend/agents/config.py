"""Portkey and model setup. This is the only place that names the model."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai.models.openai import OpenAIChatModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

REQUIRED_MODEL = "gpt-6-luna"
MODEL_NAME = os.getenv("OPENAI_MODEL") or REQUIRED_MODEL
if MODEL_NAME != REQUIRED_MODEL:
    raise RuntimeError(f"This assignment allows only {REQUIRED_MODEL}, but OPENAI_MODEL is {MODEL_NAME}.")

PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL") or "https://api.portkey.ai/v1"
MODEL_REQUEST_TIMEOUT = 45.0  # seconds per call to Portkey

# max_tokens caps each reply. Portkey's Azure route only allows function tools on gpt-6-* with reasoning off.
MODEL_SETTINGS = {"openai_reasoning_effort": "none", "max_tokens": 800}

_model: OpenAIChatModel | None = None


def build_model() -> OpenAIChatModel:
    """Return the one model and client shared by every agent."""
    global _model
    if _model is None:
        key = os.getenv("PORTKEY_API_KEY", "").strip()
        if not key:
            raise RuntimeError("PORTKEY_API_KEY is not set. Add it to hw5/.env.")
        client = AsyncOpenAI(
            api_key=key,
            base_url=PORTKEY_BASE_URL,
            default_headers={"x-portkey-api-key": key},
            timeout=MODEL_REQUEST_TIMEOUT,
            max_retries=1,
        )
        _model = OpenAIChatModel(
            MODEL_NAME,
            provider=OpenAIProvider(openai_client=client),
            settings=MODEL_SETTINGS,
        )
    return _model
