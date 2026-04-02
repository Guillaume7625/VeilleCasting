#!/usr/bin/env python3
"""Journal d'audit structuré pour VeilleCasting."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def audit_event(audit_file: Path, event_type: str, payload: dict) -> None:
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": event_type,
        **payload,
    }
    with open(audit_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def audit_decision(
    audit_file: Path,
    *,
    keep_or_reject: str,
    source_type: str,
    source_name: str,
    source_url: str,
    collected_at: str,
    raw_excerpt: str,
    paca_signal_detected: bool,
    contact_detected: bool,
    relevance_score: int,
    reject_reason: str = "",
    extra: dict | None = None,
) -> None:
    payload = {
        "source_type": source_type,
        "source_name": source_name,
        "source_url": source_url,
        "collected_at": collected_at,
        "raw_excerpt": raw_excerpt,
        "paca_signal_detected": paca_signal_detected,
        "contact_detected": contact_detected,
        "relevance_score": relevance_score,
        "keep_or_reject": keep_or_reject,
        "reject_reason": reject_reason,
    }
    if extra:
        payload.update(extra)
    audit_event(audit_file, "decision", payload)
