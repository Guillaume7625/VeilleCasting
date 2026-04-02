#!/usr/bin/env python3
"""Rendu et envoi des newsletters VeilleCasting via Resend."""

from __future__ import annotations

import hashlib
from datetime import datetime
from html import escape


def send_email(session, cfg: dict, annonces: list, log) -> bool:
    subject = "[CastINT PACA] digest — homme 40-60"
    text_body = build_plain_text_body(annonces)
    html_body = build_html_body(subject, annonces)
    payload = {
        "from": cfg["sender_email"],
        "to": [cfg["recipient_email"]],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }
    headers = {
        "Authorization": f"Bearer {cfg['resend_api_key']}",
        "Content-Type": "application/json",
        "Idempotency-Key": hashlib.sha256(
            f"{subject}|{cfg['sender_email']}|{cfg['recipient_email']}|{len(annonces)}".encode()
        ).hexdigest()[:32],
    }
    try:
        response = session.post(
            "https://api.resend.com/emails",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        log(f"Email envoye via Resend: {len(annonces)} annonce(s), id={data.get('id', 'unknown')}.")
        return True
    except Exception as e:  # noqa: BLE001
        detail = getattr(e, "response", None)
        if detail is not None:
            log(f"ERREUR envoi Resend: {e} | reponse={getattr(detail, 'text', '')}")
        else:
            log(f"ERREUR envoi Resend: {e}")
        return False


def build_plain_text_body(annonces: list) -> str:
    if not annonces:
        return "No relevant casting today"

    confirmed = sum(1 for item in annonces if item["classification"] == "CASTING_CONFIRMED")
    probable = sum(1 for item in annonces if item["classification"] == "CASTING_PROBABLE")
    men_40_60 = sum(1 for item in annonces if "men_40_60" in item.get("target_groups", []))
    model_senior = sum(1 for item in annonces if "model_senior" in item.get("target_groups", []))

    lines = [
        f"VeilleCasting - {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "BLUF:",
        f"- {confirmed} casting(s) confirme(s)",
        f"- {probable} casting(s) probable(s)",
        f"- {men_40_60} profil(s) homme 40-60",
        f"- {model_senior} profil(s) mannequin/model 40+ senior",
        "",
        "HIGH PRIORITY:",
    ]

    high_priority = [item for item in annonces if item["priority"] == "HIGH"]
    if high_priority:
        for idx, annonce in enumerate(high_priority, start=1):
            lines.extend(
                [
                    f"{idx}. {annonce['title']}",
                    f"   Type: {annonce['item_type']} | Profil: {annonce['role_label']}",
                    f"   Lieu: {annonce['location']} | Dates: {annonce['dates']}",
                    f"   Source: {annonce['source']} ({annonce['source_type']}, fiabilité {annonce['source_reliability']}, région {annonce['region']})",
                    f"   Score: {annonce['score']} | Contact: {annonce['contact_method']} - {annonce['contact_value']}",
                ]
            )
    else:
        lines.append("   Aucun casting hautement prioritaire.")

    standard = [item for item in annonces if item["priority"] != "HIGH"]
    if standard:
        lines.extend(["", "STANDARD:"])
        for idx, annonce in enumerate(standard, start=1):
            lines.extend(
                [
                    f"{idx}. {annonce['title']}",
                    f"   Type: {annonce['item_type']} | Profil: {annonce['role_label']}",
                    f"   Lieu: {annonce['location']} | Dates: {annonce['dates']}",
                    f"   Source: {annonce['source']} ({annonce['source_type']}, fiabilité {annonce['source_reliability']}, région {annonce['region']})",
                    f"   Score: {annonce['score']} | Contact: {annonce['contact_method']} - {annonce['contact_value']}",
                ]
            )

    return "\n".join(lines).strip()


def build_html_body(subject: str, annonces: list) -> str:
    if not annonces:
        return "<!doctype html><html lang='fr'><body><p>No relevant casting today</p></body></html>"

    confirmed = sum(1 for item in annonces if item["classification"] == "CASTING_CONFIRMED")
    probable = sum(1 for item in annonces if item["classification"] == "CASTING_PROBABLE")
    men_40_60 = sum(1 for item in annonces if "men_40_60" in item.get("target_groups", []))
    model_senior = sum(1 for item in annonces if "model_senior" in item.get("target_groups", []))

    def render_cards(items: list[dict]) -> str:
        cards = []
        for idx, annonce in enumerate(items, start=1):
            title = escape(annonce["title"])
            source = escape(annonce["source"])
            role = escape(annonce["role_label"])
            item_type = escape(annonce["item_type"])
            location = escape(annonce["location"])
            dates = escape(annonce["dates"])
            country = escape(annonce.get("country", "France"))
            contact_value = escape(annonce["contact_value"], quote=True)
            contact_method = escape(annonce["contact_method"])
            classification = escape(annonce["classification"])
            source_type = escape(annonce["source_type"])
            source_reliability = escape(annonce["source_reliability"])
            region = escape(annonce["region"])
            score = escape(str(annonce["score"]))
            country_line = f"<p><strong>Pays</strong> : {country}</p>" if country != "France" else ""
            if contact_method == "Lien d'application":
                link_html = f'<a href="{contact_value}">{contact_method}</a>'
            elif contact_method == "Email":
                link_html = f'<a href="mailto:{contact_value}">{contact_value}</a>'
            else:
                link_html = f'<a href="{contact_value}">{contact_value}</a>'
            cards.append(
                f"""
                <article class="card">
                  <div class="badge">{classification}</div>
                  <h3>{idx}. {title}</h3>
                  <p><strong>Type exact</strong> : {item_type}</p>
                  <p><strong>Profil recherché</strong> : {role}</p>
                  <p><strong>Lieu / dates</strong> : {location} | {dates}</p>
                  {country_line}
                  <p><strong>Source</strong> : {source} ({source_type}, fiabilité {source_reliability}, région {region})</p>
                  <p><strong>Score</strong> : {score}</p>
                  <p><strong>Contact</strong> : {link_html}</p>
                </article>
                """
            )
        return "".join(cards)

    high_priority = [item for item in annonces if item["priority"] == "HIGH"]
    standard = [item for item in annonces if item["priority"] != "HIGH"]

    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(subject)}</title>
  <style>
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#111827;line-height:1.6;background:#f8fafc}}
    .shell{{background:#fff;border:1px solid #dbe3ee;border-radius:18px;padding:24px;box-shadow:0 8px 30px rgba(15,23,42,.06)}}
    h1{{color:#0f172a;border-bottom:2px solid #2563eb;padding-bottom:.4rem;margin-top:0}}
    h2{{color:#1e40af;margin-top:2rem;margin-bottom:.6rem}}
    h3{{color:#111827;margin-bottom:.35rem}}
    a{{color:#2563eb}}
    .intro{{color:#475569}}
    .summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:1rem 0 1.5rem}}
    .summary div{{background:#eff6ff;border:1px solid #dbeafe;border-radius:14px;padding:12px}}
    .summary strong{{display:block;font-size:1.4rem;color:#1d4ed8}}
    .section-meta{{color:#64748b;font-size:.95rem;margin-top:-.25rem}}
    .card{{border:1px solid #e5e7eb;border-radius:14px;padding:14px 16px;margin:12px 0;background:#fff}}
    .badge{{display:inline-block;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:#1d4ed8;background:#dbeafe;border-radius:999px;padding:4px 8px;margin-bottom:10px}}
    @media (max-width:600px){{body{{margin:0;padding:.75rem}} .shell{{padding:16px}}}}
  </style>
</head>
<body>
  <div class="shell">
    <h1>{escape(subject)}</h1>
    <p class="intro"><strong>BLUF</strong> : {confirmed} casting(s) confirmé(s), {probable} casting(s) probable(s).</p>
    <div class="summary">
      <div><strong>{confirmed + probable}</strong> annonce(s)</div>
      <div><strong>{confirmed}</strong> confirmé(s)</div>
      <div><strong>{probable}</strong> probable(s)</div>
      <div><strong>{men_40_60}</strong> homme 40-60</div>
      <div><strong>{model_senior}</strong> modèle/senior</div>
    </div>
    <h2>HIGH PRIORITY</h2>
    <p class="section-meta">Uniquement les castings les plus pertinents et immédiatement actionnables.</p>
    {render_cards(high_priority) if high_priority else '<p>Aucun casting hautement prioritaire.</p>'}
    <h2>STANDARD</h2>
    <p class="section-meta">Opportunités valides mais moins prioritaires.</p>
    {render_cards(standard) if standard else '<p>Aucun autre casting pertinent.</p>'}
  </div>
</body>
</html>"""
