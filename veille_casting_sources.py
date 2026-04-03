#!/usr/bin/env python3
"""Collecte, qualification et déduplication des annonces VeilleCasting."""

from __future__ import annotations

import re
import time
from collections import defaultdict
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from veille_casting_audit import audit_decision
from veille_casting_config import (
    AUDIT_FILE,
    SEEN_FILE,
    load_json,
    make_hash,
    norm,
    save_json,
)
from veille_casting_openai import openai_enabled, refine_candidate_with_openai

SOURCE_METADATA = {
    "CastProd": {
        "type": "site casting",
        "reliability": "haute",
        "country": "France",
        "region": "PACA",
    },
    "Figurants PACA": {
        "type": "site figuration",
        "reliability": "haute",
        "country": "France",
        "region": "PACA",
    },
    "Facebook public": {
        "type": "social public",
        "reliability": "moyenne",
        "country": "France",
        "region": "PACA",
    },
    "Instagram public": {
        "type": "social public",
        "reliability": "moyenne",
        "country": "France",
        "region": "PACA",
    },
}

MODEL_TERMS = {
    "mannequin",
    "modele",
    "modèle",
    "model",
    "senior",
    "40+",
    "45+",
    "50+",
    "55+",
    "60+",
    "junior/senior",
}
NEWS_NOISE_TERMS = {
    "rss",
    "politique",
    "crime",
    "sante",
    "santé",
    "justice",
    "meteo",
    "météo",
    "football",
    "health",
    "culture",
}
APPLICATION_HINTS = {
    "postuler",
    "candidature",
    "appliquer",
    "apply",
    "inscription",
    "rejoindre",
    "participer",
    "envoyer",
    "voir l'annonce",
    "voir annonce",
    "dm",
    "mp",
    "message prive",
    "message privé",
    "direct message",
}
PUBLIC_BLOCK_MARKERS = (
    "log in",
    "log in to",
    "sign up",
    "create account",
    "you must log in",
    "facebook login",
    "instagram login",
    "cookies",
    "unsupported browser",
    "challenge required",
)


def get_source_metadata(source: str) -> dict:
    if source.startswith("Facebook public"):
        return SOURCE_METADATA["Facebook public"]
    if source.startswith("Instagram public"):
        return SOURCE_METADATA["Instagram public"]
    return SOURCE_METADATA.get(
        source,
        {
            "type": "source inconnue",
            "reliability": "faible",
            "country": "France",
            "region": "PACA",
        },
    )


def is_supported_source(source: str) -> bool:
    return source in SOURCE_METADATA or source.startswith("Facebook public") or source.startswith("Instagram public")


def canonical_text(*parts: str) -> str:
    return norm(" ".join(part for part in parts if part))


def is_noise(text: str) -> bool:
    return any(term in text for term in NEWS_NOISE_TERMS)


def is_casting_related(text: str, cfg: dict) -> bool:
    if any(kw in text for kw in cfg["_category_norm"]):
        return True
    if any(term in text for term in MODEL_TERMS):
        return True
    return "audition" in text or "casting" in text or "figurant" in text or "figurants" in text


def detect_target_groups(text: str) -> list[str]:
    groups: list[str] = []
    age_match = re.search(r"\b(?:4[0-9]|5[0-9]|60)\s*(?:ans?|a)?\b", text)
    if age_match and any(term in text for term in ("homme", "hommes", "h/f", "male", "masculin")):
        groups.append("men_40_60")
    if any(term in text for term in MODEL_TERMS) and (
        "senior" in text or age_match or "40+" in text or "45+" in text or "50+" in text or "55+" in text or "60+" in text
    ):
        groups.append("model_senior")
    return groups


def detect_location(text: str, cfg: dict) -> str | None:
    zones = cfg.get("zones_ok", [])
    normalized = cfg.get("_zones_norm", [])
    for idx, zone_norm in enumerate(normalized):
        if zone_norm in text:
            return zones[idx]
    return None


def detect_dates(text: str) -> str | None:
    date_match = re.search(
        r"(\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b|\b\d{4}\b|\b(?:janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre)\s+\d{4}\b|\b(?:printemps|ete|automne|hiver)\s+\d{4}\b)",
        text,
    )
    return date_match.group(1) if date_match else None


def detect_item_type(text: str) -> str:
    if any(term in text for term in ("mannequin", "modele", "modèle", "model", "senior")):
        return "mannequin / modele"
    if any(term in text for term in ("shooting", "photo", "lookbook", "catalogue", "e-commerce")):
        return "shooting / campagne"
    if any(term in text for term in ("publicite", "pub", "marque", "campagne")):
        return "pub / campagne"
    if "figurant" in text or "figurants" in text or "silhouette" in text:
        return "figuration"
    return "casting"


def score_candidate(
    text: str,
    source_meta: dict,
    target_groups: list[str],
    location: str | None,
    contact_method: str,
    item_type: str,
    explicit_casting: bool,
) -> tuple[int, str]:
    breakdown = defaultdict(int)
    breakdown["source"] = 20 if source_meta.get("reliability") == "haute" else 10
    if location:
        breakdown["location"] = 20
    if target_groups:
        breakdown["target_groups"] = 20
    if item_type in {"mannequin / modele", "pub / campagne", "shooting / campagne"}:
        breakdown["target_alignment"] = 15
    if explicit_casting:
        breakdown["explicit_casting"] = 10
    if contact_method == "Email":
        breakdown["contact"] = 10
    elif contact_method in {"Lien d'application", "DM"}:
        breakdown["contact"] = 8
    if "paca" in text or "provence" in text or "marseille" in text or "nice" in text:
        breakdown["region"] = 7
    if any(term in text for term in ("gen", "gén", "general", "général", "generic")):
        breakdown["generic_penalty"] = -12
    if not location:
        breakdown["no_location_penalty"] = -25
    score = sum(breakdown.values())
    reason = ", ".join(f"{key}:{value}" for key, value in breakdown.items())
    return score, reason


def public_html_is_blocked(html: str, url: str) -> bool:
    lowered = norm(html)
    return any(marker in lowered for marker in PUBLIC_BLOCK_MARKERS) or "/login" in url or "/accounts/login" in url


def fetch_detail_html(session, headers: dict, url: str) -> str:
    try:
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception:
        return ""


def extract_contact_value(session, headers: dict, url: str) -> tuple[str, str] | None:
    html = fetch_detail_html(session, headers, url)
    if html:
        email_match = re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", html, re.IGNORECASE)
        if email_match:
            return ("Email", email_match.group(0))

        soup = BeautifulSoup(html, "html.parser")
        mailto = soup.select_one("a[href^='mailto:']")
        if mailto and mailto.get("href"):
            email = mailto.get("href").replace("mailto:", "").strip()
            if email:
                return ("Email", email)

        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "")
            text = canonical_text(anchor.get_text(" ", strip=True))
            if any(hint in text for hint in APPLICATION_HINTS):
                if href:
                    return ("Lien d'application", urljoin(url, href) if not href.startswith("http") else href)
                break

        page_text = canonical_text(soup.get_text(" ", strip=True))
        if any(hint in page_text for hint in ("message prive", "message privé", "dm", "mp", "direct message")):
            return ("DM", url)

    return None


def social_source_specs(cfg: dict) -> list[dict]:
    social_cfg = cfg.get("social_sources", {})
    specs: list[dict] = []

    facebook_cfg = social_cfg.get("facebook_public", {})
    if facebook_cfg.get("enabled", True):
        for url in facebook_cfg.get("urls", []):
            specs.append(
                {
                    "platform": "facebook",
                    "source_name": f"Facebook public - {url}",
                    "source_url": url,
                }
            )

    instagram_cfg = social_cfg.get("instagram_public", {})
    if instagram_cfg.get("enabled", True):
        for hashtag in instagram_cfg.get("hashtags", []):
            clean = norm(hashtag).lstrip("#").replace(" ", "")
            specs.append(
                {
                    "platform": "instagram",
                    "source_name": f"Instagram public #{clean}",
                    "source_url": f"https://www.instagram.com/explore/tags/{clean}/",
                }
            )

    return specs


def extract_social_snippets(html: str, source_name: str, source_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    snippets: list[dict] = []
    seen = set()

    candidate_nodes = soup.select("article, section, li, p, div, main")
    for node in candidate_nodes:
        text = canonical_text(node.get_text(" ", strip=True))
        if len(text) < 40 or len(text) > 1200:
            continue
        if not any(
            term in text
            for term in (
                "casting",
                "audition",
                "figurant",
                "figurants",
                "mannequin",
                "modele",
                "modèle",
                "model",
                "shooting",
                "publicite",
                "pub",
                "campagne",
            )
        ):
            continue
        if text in seen:
            continue
        seen.add(text)
        link = source_url
        for anchor in node.select("a[href]"):
            href = anchor.get("href", "")
            if href:
                link = urljoin(source_url, href) if not href.startswith("http") else href
                break
        title = text.split(". ")[0][:160]
        snippets.append(
            {
                "title": title,
                "link": link,
                "description": text[:500],
                "source": source_name,
            }
        )

    if not snippets:
        meta_desc = ""
        for selector in (
            "meta[property='og:description']",
            "meta[name='description']",
            "meta[property='og:title']",
            "title",
        ):
            tag = soup.select_one(selector)
            if not tag:
                continue
            meta_desc = tag.get("content", "") if tag.name == "meta" else tag.get_text(" ", strip=True)
            if meta_desc:
                break
        meta_text = canonical_text(soup.get_text(" ", strip=True), meta_desc)
        if len(meta_text) >= 40:
            snippets.append(
                {
                    "title": meta_desc[:160] or source_name,
                    "link": source_url,
                    "description": meta_text[:500],
                    "source": source_name,
                }
            )

    return snippets


def scrape_castprod(session, headers: dict, cfg: dict, log) -> list:
    annonces = []
    base = "https://www.castprod.com"
    empty_pages = 0
    for page in range(1, 11):
        url = f"{base}/annonces/casting?page={page}"
        try:
            r = session.get(url, headers=headers, timeout=15)
            r.raise_for_status()
        except Exception as e:  # noqa: BLE001
            log(f"[castprod] Erreur page {page}: {e}")
            break
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select("article")
        if not items:
            empty_pages += 1
            if empty_pages >= 2:
                log(f"[castprod] {empty_pages} pages vides consecutives, arret.")
                break
            time.sleep(cfg.get("sleep_between_requests_seconds", 0.7))
            continue
        empty_pages = 0
        for item in items:
            title_tag = item.select_one("h2 a, h3 a, .entry-title a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            if link and not link.startswith("http"):
                link = urljoin(base, link)
            desc_tag = item.select_one("p, .entry-summary, .excerpt")
            desc = desc_tag.get_text(strip=True) if desc_tag else ""
            annonces.append({"title": title, "link": link, "description": desc, "source": "CastProd"})
        time.sleep(cfg.get("sleep_between_requests_seconds", 0.7))
    if not annonces:
        log("[castprod] ATTENTION: 0 annonce trouvee. Les selecteurs CSS ont peut-etre change.")
    return annonces


def scrape_figurants(session, headers: dict, cfg: dict, region: str, log) -> list:
    if region != "paca":
        return []
    annonces = []
    slug = "provence-alpes-cote-d-azur"
    label = "Figurants PACA"
    base = "https://www.figurants.com"
    url = f"{base}/casting/{slug}"
    try:
        r = session.get(url, headers=headers, timeout=15)
        r.raise_for_status()
    except Exception as e:  # noqa: BLE001
        log(f"[{label}] Erreur: {e}")
        return annonces
    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select("a[href*='/casting/']")
    seen_links = set()
    for tag in items:
        link = tag.get("href", "")
        if link and not link.startswith("http"):
            link = urljoin(base, link)
        if link in seen_links or "/casting/" not in link:
            continue
        seen_links.add(link)
        title = tag.get_text(strip=True)
        if len(title) < 5:
            continue
        annonces.append({"title": title, "link": link, "description": "", "source": label})
    if not annonces:
        log(f"[{label}] ATTENTION: 0 annonce trouvee. Les selecteurs CSS ont peut-etre change.")
    return annonces


def collect_social_public(session, headers: dict, cfg: dict, log) -> list[dict]:
    collected: list[dict] = []
    sleep_seconds = cfg.get("sleep_between_requests_seconds", 0.7)
    for spec in social_source_specs(cfg):
        source_name = spec["source_name"]
        source_url = spec["source_url"]
        platform = spec["platform"]
        try:
            response = session.get(source_url, headers=headers, timeout=15)
            response.raise_for_status()
            html = response.text or ""
        except Exception as exc:  # noqa: BLE001
            log(f"[{source_name}] Erreur collecte publique: {exc}")
            audit_decision(
                AUDIT_FILE,
                keep_or_reject="reject",
                source_type="social public",
                source_name=source_name,
                source_url=source_url,
                collected_at=datetime.now().isoformat(timespec="seconds"),
                raw_excerpt="",
                paca_signal_detected=True,
                contact_detected=False,
                relevance_score=0,
                reject_reason="fetch_failed",
                extra={"platform": platform},
            )
            continue

        if public_html_is_blocked(html, source_url):
            log(f"[{source_name}] Source publique non exploitable proprement (login wall / blocage).")
            audit_decision(
                AUDIT_FILE,
                keep_or_reject="reject",
                source_type="social public",
                source_name=source_name,
                source_url=source_url,
                collected_at=datetime.now().isoformat(timespec="seconds"),
                raw_excerpt="",
                paca_signal_detected=True,
                contact_detected=False,
                relevance_score=0,
                reject_reason="unsupported_source_or_login_wall",
                extra={"platform": platform},
            )
            continue

        snippets = extract_social_snippets(html, source_name, source_url)
        if not snippets:
            log(f"[{source_name}] Aucune publication exploitable extraite.")
            audit_decision(
                AUDIT_FILE,
                keep_or_reject="reject",
                source_type="social public",
                source_name=source_name,
                source_url=source_url,
                collected_at=datetime.now().isoformat(timespec="seconds"),
                raw_excerpt=canonical_text(html[:300]),
                paca_signal_detected=True,
                contact_detected=False,
                relevance_score=0,
                reject_reason="no_exploitable_public_post",
                extra={"platform": platform},
            )
            continue

        collected.extend(snippets)
        time.sleep(sleep_seconds)

    return collected


def _classify_candidate(
    annonce: dict,
    cfg: dict,
    session,
    headers: dict,
    audit_file,
    log=lambda msg: None,
) -> dict | None:
    title = annonce.get("title", "")
    description = annonce.get("description", "")
    source = annonce.get("source", "")
    link = annonce.get("link", "")
    text = canonical_text(title, description, source)
    collected_at = datetime.now().isoformat(timespec="seconds")
    source_meta = get_source_metadata(source)
    raw_excerpt = description.strip()[:400] if description else title.strip()[:400]

    if is_noise(text):
        audit_decision(
            audit_file,
            keep_or_reject="reject",
            source_type=source_meta.get("type", "source inconnue"),
            source_name=source,
            source_url=link,
            collected_at=collected_at,
            raw_excerpt=raw_excerpt,
            paca_signal_detected=False,
            contact_detected=False,
            relevance_score=0,
            reject_reason="noise_or_general_news",
        )
        return None
    if any(kw in text for kw in cfg.get("_exclude_norm", [])):
        audit_decision(
            audit_file,
            keep_or_reject="reject",
            source_type=source_meta.get("type", "source inconnue"),
            source_name=source,
            source_url=link,
            collected_at=collected_at,
            raw_excerpt=raw_excerpt,
            paca_signal_detected=False,
            contact_detected=False,
            relevance_score=0,
            reject_reason="excluded_keyword",
        )
        return None
    if not is_casting_related(text, cfg):
        audit_decision(
            audit_file,
            keep_or_reject="reject",
            source_type=source_meta.get("type", "source inconnue"),
            source_name=source,
            source_url=link,
            collected_at=collected_at,
            raw_excerpt=raw_excerpt,
            paca_signal_detected=False,
            contact_detected=False,
            relevance_score=0,
            reject_reason="not_casting_related",
        )
        return None

    contact = extract_contact_value(session, headers, link)
    if not contact:
        audit_decision(
            audit_file,
            keep_or_reject="reject",
            source_type=source_meta.get("type", "source inconnue"),
            source_name=source,
            source_url=link,
            collected_at=collected_at,
            raw_excerpt=raw_excerpt,
            paca_signal_detected=False,
            contact_detected=False,
            relevance_score=0,
            reject_reason="no_exploitable_contact",
        )
        return None
    contact_method, contact_value = contact

    target_groups = detect_target_groups(text)
    location = detect_location(text, cfg)
    dates = detect_dates(text)
    item_type = detect_item_type(text)

    explicit_casting = "casting" in text or "figurant" in text or "figurants" in text or "audition" in text or "recherche" in text
    if not is_supported_source(source):
        audit_decision(
            audit_file,
            keep_or_reject="reject",
            source_type="source inconnue",
            source_name=source,
            source_url=link,
            collected_at=collected_at,
            raw_excerpt=raw_excerpt,
            paca_signal_detected=False,
            contact_detected=True,
            relevance_score=0,
            reject_reason="unsupported_source",
        )
        return None

    if source == "Figurants PACA" and not location:
        location = "PACA"
    if source == "CastProd" and not location:
        audit_decision(
            audit_file,
            keep_or_reject="reject",
            source_type=source_meta.get("type", "source inconnue"),
            source_name=source,
            source_url=link,
            collected_at=collected_at,
            raw_excerpt=raw_excerpt,
            paca_signal_detected=False,
            contact_detected=True,
            relevance_score=0,
            reject_reason="missing_paca_location",
        )
        return None

    if not (explicit_casting or target_groups or item_type != "casting"):
        audit_decision(
            audit_file,
            keep_or_reject="reject",
            source_type=source_meta.get("type", "source inconnue"),
            source_name=source,
            source_url=link,
            collected_at=collected_at,
            raw_excerpt=raw_excerpt,
            paca_signal_detected=bool(location or source_meta.get("region") == "PACA"),
            contact_detected=True,
            relevance_score=0,
            reject_reason="too_vague",
        )
        return None

    base_score, score_reason = score_candidate(
        text=text,
        source_meta=source_meta,
        target_groups=target_groups,
        location=location,
        contact_method=contact_method,
        item_type=item_type,
        explicit_casting=explicit_casting,
    )

    ai_refinement = None
    if openai_enabled(cfg):
        ai_refinement = refine_candidate_with_openai(
            session,
            cfg,
            {
                **annonce,
                "classification": "CASTING_PROBABLE",
                "priority": "STANDARD",
                "item_type": item_type,
                "role_label": "Casting général",
                "target_groups": target_groups,
                "location": location or source_meta.get("region", "PACA"),
                "dates": dates or "Non précisées",
                "contact_method": contact_method,
                "contact_value": contact_value,
                "score": base_score,
            },
            log,
        )

    ai_used = bool(ai_refinement)
    ai_score = base_score
    ai_confidence = 0
    ai_summary = ""
    ai_model = ""
    newsletter_title = title
    if ai_refinement:
        if not ai_refinement.get("keep", True) and ai_refinement.get("confidence", 0) >= 60:
            audit_decision(
                audit_file,
                keep_or_reject="reject",
                source_type=source_meta.get("type", "source inconnue"),
                source_name=source,
                source_url=link,
                collected_at=collected_at,
                raw_excerpt=raw_excerpt,
                paca_signal_detected=bool(location or source_meta.get("region") == "PACA"),
                contact_detected=True,
                relevance_score=base_score,
                reject_reason="openai_rejected",
                extra={
                    "ai_used": True,
                    "ai_model": ai_refinement.get("model", ""),
                    "ai_confidence": ai_refinement.get("confidence", 0),
                    "ai_score": ai_refinement.get("ai_score", base_score),
                    "ai_reason": ai_refinement.get("reason", ""),
                },
            )
            return None

        target_groups = ai_refinement.get("target_groups", target_groups) or target_groups
        location = ai_refinement.get("location", location) or location
        dates = ai_refinement.get("dates", dates) or dates
        contact_method = ai_refinement.get("contact_method", contact_method) or contact_method
        contact_value = ai_refinement.get("contact_value", contact_value) or contact_value
        item_type = ai_refinement.get("item_type", item_type) or item_type
        newsletter_title = ai_refinement.get("newsletter_title", title) or title
        ai_summary = ai_refinement.get("summary", "") or ""
        ai_score = ai_refinement.get("ai_score", base_score)
        ai_confidence = ai_refinement.get("confidence", 0)
        ai_model = ai_refinement.get("model", "")

    score = round((base_score * 0.65) + (ai_score * 0.35)) if ai_used else base_score
    score_reason = f"{score_reason}; ai_score:{ai_score}; ai_confidence:{ai_confidence}" if ai_used else score_reason

    if source_meta.get("type") == "social public":
        classification = "CASTING_PROBABLE"
    elif score >= 85 or (source == "Figurants PACA" and (explicit_casting or target_groups)):
        classification = "CASTING_CONFIRMED"
    else:
        classification = "CASTING_PROBABLE"

    priority = "HIGH" if score >= 80 or target_groups or item_type in {"mannequin / modele", "pub / campagne", "shooting / campagne"} else "STANDARD"
    if ai_refinement and ai_refinement.get("priority") == "HIGH":
        priority = "HIGH"
    role_label = "Casting général"
    if "model_senior" in target_groups:
        role_label = "Mannequin / modèle 40+ senior"
    elif "men_40_60" in target_groups:
        role_label = "Homme 40-60 ans"
    elif item_type == "mannequin / modele":
        role_label = "Profil mannequin / modèle"
    elif item_type == "pub / campagne":
        role_label = "Campagne / publicité"
    elif item_type == "shooting / campagne":
        role_label = "Shooting / campagne"
    elif item_type == "figuration":
        role_label = "Figurants / silhouettes"
    if ai_refinement:
        role_label = ai_refinement.get("role_label", role_label) or role_label

    reason_parts = [
        f"source={source}",
        f"type={item_type}",
        f"score={score}",
        f"contact={contact_method}",
    ]
    if location:
        reason_parts.append(f"location={location}")
    if target_groups:
        reason_parts.append(f"target_groups={','.join(target_groups)}")
    if ai_used:
        reason_parts.append(f"ai_model={ai_model or 'unknown'}")
        reason_parts.append(f"ai_confidence={ai_confidence}")

    result = {
        **annonce,
        "classification": classification,
        "priority": priority,
        "target_groups": target_groups,
        "role_label": role_label,
        "item_type": item_type,
        "country": source_meta.get("country", "France"),
        "region": source_meta.get("region", "PACA"),
        "source_type": source_meta.get("type", "source inconnue"),
        "source_reliability": source_meta.get("reliability", "faible"),
        "collected_at": collected_at,
        "raw_excerpt": raw_excerpt,
        "classification_reason": " | ".join(reason_parts),
        "score": score,
        "score_reason": score_reason,
        "location": location or source_meta.get("region", "PACA"),
        "dates": dates or "Non précisées",
        "contact_method": contact_method,
        "contact_value": contact_value,
        "newsletter_title": newsletter_title,
        "ai_used": ai_used,
        "ai_model": ai_model,
        "ai_confidence": ai_confidence,
        "ai_score": ai_score,
        "ai_summary": ai_summary,
    }
    audit_decision(
        audit_file,
        keep_or_reject="keep",
        source_type=result["source_type"],
        source_name=source,
        source_url=link,
        collected_at=collected_at,
        raw_excerpt=raw_excerpt,
        paca_signal_detected=bool(location or source_meta.get("region") == "PACA"),
        contact_detected=True,
        relevance_score=score,
        extra={
            "classification": classification,
            "priority": priority,
            "reason": result["classification_reason"],
            "ai_used": ai_used,
            "ai_model": ai_model,
            "ai_confidence": ai_confidence,
            "ai_score": ai_score,
            "ai_summary": ai_summary,
        },
    )
    return result


def prepare_newsletter_items(annonces: list[dict], cfg: dict, session, headers: dict, audit_file, log=lambda msg: None) -> list[dict]:
    prepared: list[dict] = []
    for annonce in annonces:
        item = _classify_candidate(annonce, cfg, session, headers, audit_file, log)
        if item:
            prepared.append(item)
    priority_order = {"HIGH": 0, "STANDARD": 1}
    classification_order = {"CASTING_CONFIRMED": 0, "CASTING_PROBABLE": 1}
    return sorted(
        prepared,
        key=lambda item: (
            priority_order.get(item.get("priority", "STANDARD"), 99),
            classification_order.get(item.get("classification", "CASTING_PROBABLE"), 99),
            -int(item.get("score", 0)),
            item.get("source", ""),
            item.get("title", ""),
        ),
    )


def filter_new(annonces: list) -> list:
    seen = load_json(SEEN_FILE, [])
    seen_set = set(seen)
    new = []
    for a in annonces:
        h = make_hash(a["title"], a["link"])
        if h not in seen_set:
            a["_hash"] = h
            new.append(a)
    return new


def mark_seen(annonces: list) -> None:
    seen = load_json(SEEN_FILE, [])
    for a in annonces:
        seen.append(a["_hash"])
    save_json(SEEN_FILE, seen[-5000:])
