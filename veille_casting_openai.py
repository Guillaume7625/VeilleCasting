#!/usr/bin/env python3
"""Enrichissement optionnel des annonces via l'API OpenAI."""

from __future__ import annotations

import json
import os
from typing import Any

DEFAULT_OPENAI_MODEL = "gpt-5.1-mini"
TARGET_GROUP_WHITELIST = {"men_40_60", "model_senior"}
ITEM_TYPE_WHITELIST = {
    "casting",
    "figuration",
    "mannequin / modele",
    "pub / campagne",
    "shooting / campagne",
}
CONTACT_METHOD_WHITELIST = {"Email", "Lien d'application", "DM"}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        numeric = int(float(value))
    except Exception:  # noqa: BLE001
        return default
    return max(minimum, min(maximum, numeric))


def _extract_output_text(data: dict) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    chunks: list[str] = []
    for output in data.get("output", []) or []:
        for content in output.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
    return "\n".join(chunks).strip()


def openai_api_key(cfg: dict) -> str:
    key = _clean_text(cfg.get("openai_api_key", ""))
    if key and key.lower() not in {"votre_cle_api_openai", "your_openai_api_key"}:
        return key
    return _clean_text(os.environ.get("OPENAI_API_KEY", ""))


def openai_enabled(cfg: dict) -> bool:
    return bool(openai_api_key(cfg))


def refine_candidate_with_openai(session, cfg: dict, candidate: dict, log) -> dict | None:
    api_key = openai_api_key(cfg)
    if not api_key:
        return None

    model = _clean_text(cfg.get("openai_model", "")) or DEFAULT_OPENAI_MODEL
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Tu qualifies des annonces de casting pour une newsletter PACA. "
                            "Reste strict: PACA uniquement, contact exploitable obligatoire, "
                            "pas de news générales, pas de bruit, pas d'items vagues. "
                            "Tu ne dois pas inventer d'information. "
                            "Si l'annonce n'est pas une vraie opportunité casting/mannequin/pub/shooting/figuration PACA, "
                            "retourne keep=false."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(
                            {
                                "title": candidate.get("title", ""),
                                "description": candidate.get("description", ""),
                                "source": candidate.get("source", ""),
                                "link": candidate.get("link", ""),
                                "current_extraction": {
                                    "classification": candidate.get("classification", ""),
                                    "priority": candidate.get("priority", ""),
                                    "item_type": candidate.get("item_type", ""),
                                    "role_label": candidate.get("role_label", ""),
                                    "target_groups": candidate.get("target_groups", []),
                                    "location": candidate.get("location", ""),
                                    "dates": candidate.get("dates", ""),
                                    "contact_method": candidate.get("contact_method", ""),
                                    "contact_value": candidate.get("contact_value", ""),
                                    "score": candidate.get("score", 0),
                                },
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                    }
                ],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "veille_casting_refinement",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "keep": {"type": "boolean"},
                        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                        "ai_score": {"type": "integer", "minimum": 0, "maximum": 100},
                        "classification": {
                            "type": "string",
                            "enum": ["CASTING_CONFIRMED", "CASTING_PROBABLE", "REJECT"],
                        },
                        "priority": {"type": "string", "enum": ["HIGH", "STANDARD"]},
                        "item_type": {"type": "string"},
                        "role_label": {"type": "string"},
                        "newsletter_title": {"type": "string"},
                        "summary": {"type": "string"},
                        "location": {"type": "string"},
                        "dates": {"type": "string"},
                        "contact_method": {"type": "string"},
                        "contact_value": {"type": "string"},
                        "target_groups": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "reason": {"type": "string"},
                    },
                    "required": [
                        "keep",
                        "confidence",
                        "ai_score",
                        "classification",
                        "priority",
                        "item_type",
                        "role_label",
                        "newsletter_title",
                        "summary",
                        "location",
                        "dates",
                        "contact_method",
                        "contact_value",
                        "target_groups",
                        "reason",
                    ],
                },
            }
        },
        "max_output_tokens": 500,
        "temperature": 0.1,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = session.post(
            "https://api.openai.com/v1/responses",
            headers=headers,
            json=payload,
            timeout=float(cfg.get("openai_timeout_seconds", 45)),
        )
        response.raise_for_status()
        data = response.json()
        raw_text = _extract_output_text(data)
        if not raw_text:
            log(f"[OpenAI] Reponse vide pour {candidate.get('title', '')}.")
            return None
        parsed = json.loads(raw_text)
    except Exception as exc:  # noqa: BLE001
        log(f"[OpenAI] Echec refinement: {exc}")
        return None

    classification = _clean_text(parsed.get("classification", "CASTING_PROBABLE"))
    if classification not in {"CASTING_CONFIRMED", "CASTING_PROBABLE", "REJECT"}:
        classification = "CASTING_PROBABLE"

    priority = _clean_text(parsed.get("priority", "STANDARD"))
    if priority not in {"HIGH", "STANDARD"}:
        priority = "STANDARD"

    item_type = _clean_text(parsed.get("item_type", candidate.get("item_type", "casting")))
    role_label = _clean_text(parsed.get("role_label", candidate.get("role_label", "Casting général")))
    newsletter_title = _clean_text(parsed.get("newsletter_title", candidate.get("title", "")))
    summary = _clean_text(parsed.get("summary", ""))
    location = _clean_text(parsed.get("location", candidate.get("location", "")))
    dates = _clean_text(parsed.get("dates", candidate.get("dates", "")))
    contact_method = _clean_text(parsed.get("contact_method", candidate.get("contact_method", "")))
    contact_value = _clean_text(parsed.get("contact_value", candidate.get("contact_value", "")))
    reason = _clean_text(parsed.get("reason", ""))
    confidence = _clamp_int(parsed.get("confidence"), 0, 100, 50)
    ai_score = _clamp_int(parsed.get("ai_score"), 0, 100, candidate.get("score", 0))

    target_groups = [
        group
        for group in parsed.get("target_groups", [])
        if isinstance(group, str) and group in TARGET_GROUP_WHITELIST
    ]
    if item_type not in ITEM_TYPE_WHITELIST:
        item_type = candidate.get("item_type", "casting")
    if contact_method not in CONTACT_METHOD_WHITELIST:
        contact_method = candidate.get("contact_method", "Lien d'application")

    return {
        "keep": bool(parsed.get("keep", True)),
        "confidence": confidence,
        "ai_score": ai_score,
        "classification": classification,
        "priority": priority,
        "item_type": item_type,
        "role_label": role_label,
        "newsletter_title": newsletter_title,
        "summary": summary,
        "location": location,
        "dates": dates,
        "contact_method": contact_method,
        "contact_value": contact_value,
        "target_groups": target_groups,
        "reason": reason,
        "model": model,
    }
