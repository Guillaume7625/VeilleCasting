#!/usr/bin/env python3
"""VeilleCasting - orchestrateur principal."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from veille_casting_config import APP_DIR, AUDIT_FILE, DEFAULT_CONFIG, config_is_filled, load_config, log, save_json
from veille_casting_newsletter import send_email
from veille_casting_status import write_status
from veille_casting_sources import (
    collect_social_public,
    filter_new,
    mark_seen,
    prepare_newsletter_items,
    scrape_castprod,
    scrape_figurants,
)

SESSION = requests.Session()
_retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
SESSION.mount("https://", HTTPAdapter(max_retries=_retries))
SESSION.mount("http://", HTTPAdapter(max_retries=_retries))
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def cmd_init() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    (APP_DIR / "public").mkdir(parents=True, exist_ok=True)
    if not (APP_DIR / "config.json").exists():
        save_json(APP_DIR / "config.json", DEFAULT_CONFIG)
        log("Config par defaut creee.")
    config_path = APP_DIR / "config.json"
    editor = os.environ.get("EDITOR", "").strip()
    opened = False
    if editor:
        try:
            subprocess.Popen([editor, str(config_path)])
            opened = True
        except Exception:
            opened = False
    if not opened:
        if sys.platform.startswith("linux"):
            try:
                subprocess.Popen(["xdg-open", str(config_path)])
                opened = True
            except Exception:
                opened = False
    if not opened:
        log(f"Editez manuellement : {config_path}")
    log(f"--init termine. Config: {config_path}")


def run_once() -> None:
    log("=== Debut de la veille ===")
    cfg = load_config()
    if not config_is_filled(cfg):
        if cfg.get("_legacy_gmail_config"):
            log("Ancienne config Gmail detectee. Lancez --init pour reconfigurer Resend.")
        else:
            log("Config non remplie. Lancez --init pour configurer.")
        return
    if cfg.get("openai_api_key"):
        log(f"IA OpenAI activee avec le modele {cfg.get('openai_model', 'gpt-5.1-mini')}.")

    all_annonces = []
    sources = cfg.get("sources", {})
    if sources.get("castprod", True):
        all_annonces.extend(scrape_castprod(SESSION, HEADERS, cfg, log))
    if sources.get("figurants_paca", True):
        all_annonces.extend(scrape_figurants(SESSION, HEADERS, cfg, "paca", log))

    social_items = collect_social_public(SESSION, HEADERS, cfg, log)
    if social_items:
        all_annonces.extend(social_items)
        log(f"Collecte sociale publique: {len(social_items)} item(s) brut(s).")

    log(f"Total brut: {len(all_annonces)} annonce(s).")
    relevant = prepare_newsletter_items(all_annonces, cfg, SESSION, HEADERS, AUDIT_FILE, log)
    confirmed = sum(1 for item in relevant if item["classification"] == "CASTING_CONFIRMED")
    probable = sum(1 for item in relevant if item["classification"] == "CASTING_PROBABLE")
    model_senior = sum(1 for item in relevant if "model_senior" in item.get("target_groups", []))
    men_40_60 = sum(1 for item in relevant if "men_40_60" in item.get("target_groups", []))
    log(
        "Apres filtrage: "
        f"{len(relevant)} annonce(s) pertinente(s), "
        f"{confirmed} confirmee(s), {probable} probable(s), "
        f"{men_40_60} homme 40-60, {model_senior} modele/senior."
    )
    if not relevant:
        log("No relevant casting today")
        publish_status(cfg, all_annonces, relevant, new_count=0, mail_status="No relevant casting today")
        if send_email(SESSION, cfg, relevant, log):
            log("Newsletter vide envoyee via Resend.")
        return

    new = filter_new(relevant)
    log(f"Nouvelles: {len(new)} annonce(s).")
    if new:
        if send_email(SESSION, cfg, new, log):
            mark_seen(new)
            mail_status = "Mail envoye"
        else:
            log("Email non envoye, annonces NON marquees comme vues.")
            mail_status = "Echec envoi mail"
    else:
        log("Aucune nouvelle annonce.")
        mail_status = "Aucun nouveau mail"
    publish_status(cfg, all_annonces, relevant, new_count=len(new), mail_status=mail_status)
    log("=== Fin de la veille ===")


def publish_status(cfg: dict, all_annonces: list, relevant: list, *, new_count: int, mail_status: str) -> None:
    public_dir = APP_DIR / "public"
    status = {
        "title": "CastINT PACA",
        "last_run": datetime.now().isoformat(timespec="seconds"),
        "mail_status": mail_status,
        "source_count": len(all_annonces),
        "relevant_count": len(relevant),
        "new_count": new_count,
        "confirmed_count": sum(1 for item in relevant if item["classification"] == "CASTING_CONFIRMED"),
        "probable_count": sum(1 for item in relevant if item["classification"] == "CASTING_PROBABLE"),
        "openai_enabled": bool(cfg.get("openai_api_key")),
        "latest_items": [
            {
                "title": item.get("newsletter_title") or item.get("title", ""),
                "role_label": item.get("role_label", ""),
                "location": item.get("location", ""),
                "source": item.get("source", ""),
                "contact_method": item.get("contact_method", ""),
            }
            for item in relevant[:6]
        ],
    }
    write_status(public_dir, status)


def main() -> None:
    parser = argparse.ArgumentParser(description="Veille Casting automatique")
    parser.add_argument("--init", action="store_true", help="Creer ou ouvrir la configuration")
    parser.add_argument("--once", action="store_true", help="Lancer une veille (comportement par defaut)")
    args = parser.parse_args()
    if args.init:
        cmd_init()
        return
    try:
        run_once()
    except Exception as e:  # noqa: BLE001
        log(f"ERREUR FATALE NON GEREE: {e}")


if __name__ == "__main__":
    main()
