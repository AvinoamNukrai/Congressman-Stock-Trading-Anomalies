"""Shared Gemini API utilities with retry and optional Pydantic schema parsing.

Automatically consumes [gemini] section in config.ini if present for default
parameters unless explicit overrides are provided.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional, Type

# Lazy import so other functionality works without the dependency (e.g. dry run)
try:  # pragma: no cover
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
except ImportError:  # pragma: no cover
    genai = None  # type: ignore
    types = None  # type: ignore

from pydantic import BaseModel

from .load_config import load_config, get_api_key

_DEFAULTS = {
    "model_name": None,  # resolved later from other sections if absent
    "temperature": 0.2,
    "top_p": 0.9,
    "max_output_tokens": 768,
    "max_retries": 3,
    "base_wait": 2.0,
}


def _load_gemini_section() -> dict:
    parser = load_config()
    if not parser.has_section("gemini"):
        return dict(_DEFAULTS)
    data = dict(_DEFAULTS)
    section = parser["gemini"]
    for key in list(_DEFAULTS.keys()):
        if key in section and section[key] != "":
            raw = section[key].strip()
            if key in {"temperature", "top_p", "base_wait"}:
                try:
                    data[key] = float(raw)
                except ValueError:
                    logging.warning("Invalid float for gemini.%s: %s", key, raw)
            elif key in {"max_output_tokens", "max_retries"}:
                try:
                    data[key] = int(raw)
                except ValueError:
                    logging.warning("Invalid int for gemini.%s: %s", key, raw)
            else:
                data[key] = raw
    return data


def call_gemini(
    prompt: str,
    *,
    model_name: Optional[str] = None,
    response_schema: Optional[Type[BaseModel]] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_output_tokens: Optional[int] = None,
    max_retries: Optional[int] = None,
    base_wait: Optional[float] = None,
    api_key: Optional[str] = None,
) -> Optional[dict]:
    """Invoke Gemini model returning parsed dict or None.

    Order of precedence for parameters: explicit argument > [gemini] config > defaults.
    If response_schema is provided (Pydantic BaseModel subclass), attempt structured parsing.
    """
    cfg_defaults = _load_gemini_section()

    model_name = model_name or cfg_defaults.get("model_name")
    temperature = temperature if temperature is not None else cfg_defaults["temperature"]
    top_p = top_p if top_p is not None else cfg_defaults["top_p"]
    max_output_tokens = (
        max_output_tokens if max_output_tokens is not None else cfg_defaults["max_output_tokens"]
    )
    max_retries = max_retries if max_retries is not None else cfg_defaults["max_retries"]
    base_wait = base_wait if base_wait is not None else cfg_defaults["base_wait"]

    if model_name is None:
        # fallback: attempt to reuse model from create_transactions_dataset section
        try:
            parser = load_config()
            if parser.has_section("create_transactions_dataset"):
                model_name = parser.get("create_transactions_dataset", "model_name", fallback=None)
        except Exception:  # noqa
            pass
    if model_name is None:
        logging.error("No Gemini model_name specified.")
        return None

    if genai is None or types is None:
        logging.error("google-genai not installed; cannot call Gemini.")
        return None

    if api_key is None:
        try:
            api_key = get_api_key("gemini")
        except Exception as e:  # noqa
            logging.error("API key retrieval failed: %s", e)
            return None

    client = genai.Client(api_key=api_key)

    config_kwargs = {
        "temperature": temperature,
        "top_p": top_p,
        "max_output_tokens": max_output_tokens,
        "response_mime_type": "application/json" if response_schema else None,
        "response_schema": response_schema if response_schema else None,
    }
    # remove None values
    config_kwargs = {k: v for k, v in config_kwargs.items() if v is not None}

    try:
        gen_config = types.GenerateContentConfig(**config_kwargs)
    except Exception as e:  # noqa
        logging.error("Failed building GenerateContentConfig: %s", e)
        return None

    for attempt in range(1, (max_retries or 1) + 1):
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=gen_config,
            )
            # Structured parsing path
            if response_schema and getattr(resp, "parsed", None):
                try:
                    return resp.parsed.model_dump()  # type: ignore[attr-defined]
                except Exception as e:  # noqa
                    logging.warning("Parsed object dump failed: %s", e)
            # Fallback to text
            if getattr(resp, "text", None):
                raw_text = resp.text
                if response_schema:
                    try:
                        obj = response_schema.model_validate_json(raw_text)
                        return obj.model_dump()
                    except Exception as e:  # noqa
                        logging.warning(
                            "Schema validation error attempt %d: %s | raw len=%d",
                            attempt,
                            e,
                            len(raw_text or ""),
                        )
                # Try raw JSON decode
                try:
                    return json.loads(raw_text)
                except Exception:
                    return {"raw": raw_text}
            logging.error("Empty Gemini response (attempt %d)", attempt)
        except Exception as e:  # noqa
            wait = (base_wait or 2.0) * attempt
            logging.warning(
                "Gemini call error '%s' attempt %d/%d retrying in %.1fs", e, attempt, max_retries, wait
            )
            if attempt >= (max_retries or 1):
                break
            time.sleep(wait)
    return None

__all__ = ["call_gemini"]

