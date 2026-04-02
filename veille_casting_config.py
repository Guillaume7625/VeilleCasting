#!/usr/bin/env python3
"""Configuration, chemins et utilitaires partagés pour VeilleCasting."""

from __future__ import annotations

import hashlib
import json
import os
import unicodedata
from datetime import datetime
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA", ".")) / "VeilleCasting"
CONFIG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "veille.log"
SEEN_FILE = APP_DIR / "seen_hashes.json"
AUDIT_FILE = APP_DIR / "audit.jsonl"

DEFAULT_CONFIG = {
    "resend_api_key": "VOTRE_CLE_API_RESEND",
    "sender_email": "VeilleCasting <newsletter@votre-domaine.fr>",
    "recipient_email": "piccinno@hotmail.com",
    "zones_ok": [
        "paca",
        "provence",
        "alpes",
        "cote d'azur",
        "cote d azur",
        "bouches-du-rhone",
        "bouches du rhone",
        "var",
        "vaucluse",
        "alpes-maritimes",
        "alpes maritimes",
        "nice",
        "marseille",
        "toulon",
        "avignon",
        "cannes",
        "aix-en-provence",
        "aix en provence",
        "frejus",
        "menton",
        "antibes",
        "grasse",
        "draguignan",
        "istres",
        "martigues",
        "gap",
        "manosque",
        "toute la france",
        "france entiere",
        "national",
    ],
    "category_keywords": [
        "figuration",
        "figurant",
        "figurante",
        "casting",
        "acteur",
        "actrice",
        "comedien",
        "comedienne",
        "doublure",
        "silhouette",
        "role muet",
        "extra",
        "film",
        "serie",
        "television",
        "tv",
        "court-metrage",
        "court metrage",
        "long-metrage",
        "long metrage",
        "publicite",
        "pub",
        "clip",
        "clip video",
        "theatre",
        "spectacle",
        "shooting",
        "campagne",
        "marque",
        "catalogue",
        "e-commerce",
        "commerce",
        "lookbook",
        "mode",
    ],
    "exclude_keywords": [
        "animateur",
        "animatrice",
        "voix off",
        "voice over",
        "danse",
        "danseur",
        "danseuse",
        "chant",
        "chanteur",
        "chanteuse",
        "humour",
        "stand up",
        "podcast",
    ],
    "sources": {
        "castprod": True,
        "figurants_paca": True,
    },
    "social_sources": {
        "facebook_public": {
            "enabled": True,
            "urls": [
                "https://www.facebook.com/groups/castingmarseille/",
                "https://www.facebook.com/groups/castingfigurantspaca/",
                "https://www.facebook.com/groups/figurantssud/",
            ],
        },
        "instagram_public": {
            "enabled": True,
            "hashtags": [
                "castingpaca",
                "castingmarseille",
                "figurantpaca",
                "modelepaca",
                "mannequinpaca",
                "seniormodele",
            ],
        },
    },
    "sleep_between_requests_seconds": 0.7,
}


def norm(text: str) -> str:
    """Minuscule + suppression des accents."""
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def log(msg: str) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def load_json(path: Path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: Path, data) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def make_hash(title: str, link: str) -> str:
    return hashlib.sha256(f"{title}|{link}".encode()).hexdigest()[:16]


def load_config() -> dict:
    cfg = load_json(CONFIG_FILE, None)
    if cfg is None:
        log("Config absente, creation du fichier par defaut.")
        save_json(CONFIG_FILE, DEFAULT_CONFIG)
        cfg = DEFAULT_CONFIG.copy()
    if "social_sources" not in cfg:
        cfg["social_sources"] = DEFAULT_CONFIG["social_sources"]
    if "sender_password" in cfg and "resend_api_key" not in cfg:
        cfg["_legacy_gmail_config"] = True
    cfg["_exclude_norm"] = [norm(x) for x in cfg.get("exclude_keywords", [])]
    cfg["_category_norm"] = [norm(x) for x in cfg.get("category_keywords", [])]
    cfg["_zones_norm"] = [norm(x) for x in cfg.get("zones_ok", [])]
    return cfg


def config_is_filled(cfg: dict) -> bool:
    return (
        cfg.get("resend_api_key", "") not in ("", DEFAULT_CONFIG["resend_api_key"])
        and cfg.get("sender_email", "") not in ("", DEFAULT_CONFIG["sender_email"])
    )
