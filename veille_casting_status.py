#!/usr/bin/env python3
"""Publication d'un statut statique pour le sous-domaine VeilleCasting."""

from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path


def _summary_value(value: object) -> str:
    return escape(str(value))


def build_status_html(status: dict) -> str:
    title = escape(status.get("title", "CastINT PACA"))
    generated_at = escape(status.get("generated_at", ""))
    last_run = escape(status.get("last_run", ""))
    mail_status = escape(status.get("mail_status", ""))
    source_count = escape(str(status.get("source_count", 0)))
    relevant_count = escape(str(status.get("relevant_count", 0)))
    new_count = escape(str(status.get("new_count", 0)))
    confirmed_count = escape(str(status.get("confirmed_count", 0)))
    probable_count = escape(str(status.get("probable_count", 0)))
    openai_mode = escape("oui" if status.get("openai_enabled") else "non")
    latest_items = status.get("latest_items", []) or []
    item_blocks = []
    for item in latest_items[:6]:
        item_blocks.append(
            f"""
            <li>
              <strong>{escape(item.get('title', ''))}</strong><br>
              {escape(item.get('role_label', ''))} - {escape(item.get('location', ''))}<br>
              {escape(item.get('source', ''))} - {escape(item.get('contact_method', ''))}
            </li>
            """
        )
    items_html = "".join(item_blocks) if item_blocks else "<li>Aucun item récent.</li>"
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>{title}</title>
  <style>
    :root{{color-scheme:light;--bg:#f5f7fb;--card:#fff;--ink:#0f172a;--muted:#64748b;--accent:#1d4ed8;--line:#dbe3ee}}
    body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:linear-gradient(180deg,#eef4ff 0%,#f5f7fb 24%,#f8fafc 100%);color:var(--ink)}}
    .wrap{{max-width:980px;margin:0 auto;padding:32px 18px 48px}}
    .hero{{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:28px;box-shadow:0 8px 30px rgba(15,23,42,.06)}}
    h1{{margin:0 0 6px;font-size:2rem;letter-spacing:-.03em}}
    .sub{{color:var(--muted);margin:0 0 22px}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:18px 0}}
    .metric{{background:#eff6ff;border:1px solid #dbeafe;border-radius:16px;padding:14px}}
    .metric strong{{display:block;font-size:1.7rem;color:var(--accent)}}
    .section{{margin-top:26px}}
    .section h2{{margin:0 0 10px;font-size:1.2rem}}
    ul{{padding-left:20px;line-height:1.55}}
    .meta{{color:var(--muted);font-size:.95rem}}
    .badge{{display:inline-block;padding:4px 10px;border-radius:999px;background:#dcfce7;color:#166534;font-weight:700}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div class="badge">VeilleCasting</div>
      <h1>{title}</h1>
      <p class="sub">Sous-domaine de statut statique pour le suivi PACA. Mise à jour automatique à chaque exécution du worker.</p>
      <div class="grid">
        <div class="metric"><strong>{_summary_value(relevant_count)}</strong>Annonces pertinentes</div>
        <div class="metric"><strong>{_summary_value(new_count)}</strong>Nouvelles</div>
        <div class="metric"><strong>{_summary_value(confirmed_count)}</strong>Confirmées</div>
        <div class="metric"><strong>{_summary_value(probable_count)}</strong>Probables</div>
        <div class="metric"><strong>{_summary_value(source_count)}</strong>Sources brutes</div>
        <div class="metric"><strong>{openai_mode}</strong>IA OpenAI</div>
      </div>
      <div class="section">
        <h2>Dernier run</h2>
        <p class="meta">{last_run} - {mail_status}</p>
      </div>
      <div class="section">
        <h2>Derniers items</h2>
        <ul>{items_html}</ul>
      </div>
      <div class="section">
        <h2>Statut technique</h2>
        <p class="meta">Généré le {generated_at}</p>
      </div>
    </div>
  </div>
</body>
</html>"""


def write_status(public_dir: Path, status: dict) -> None:
    public_dir.mkdir(parents=True, exist_ok=True)
    status = dict(status)
    status.setdefault("generated_at", datetime.now().isoformat(timespec="seconds"))
    (public_dir / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    (public_dir / "index.html").write_text(build_status_html(status), encoding="utf-8")
