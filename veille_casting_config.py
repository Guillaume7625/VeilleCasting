#!/usr/bin/env python3
"""Configuration, chemins et utilitaires partagés pour VeilleCasting."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import unicodedata
from datetime import datetime
from pathlib import Path

def _default_app_dir() -> Path:
    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        return Path(appdata) / "VeilleCasting"
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if xdg_config_home:
        return Path(xdg_config_home) / "VeilleCasting"
    return Path.home() / ".config" / "VeilleCasting"


APP_DIR = Path(os.environ.get("VEILLECASTING_DATA_DIR", "")) if os.environ.get("VEILLECASTING_DATA_DIR", "").strip() else _default_app_dir()
CONFIG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "veille.log"
SEEN_FILE = APP_DIR / "seen_hashes.json"
AUDIT_FILE = APP_DIR / "audit.jsonl"
DEFAULT_SENDER_EMAIL = "noreply@example.com"
DEFAULT_OPENAI_MODEL = "gpt-5.1-mini"

DEFAULT_CONFIG = {
    "resend_api_key": "VOTRE_CLE_API_RESEND",
    "sender_email": DEFAULT_SENDER_EMAIL,
    "recipient_email": "votre-email@example.com",
    "openai_api_key": "",
    "openai_model": DEFAULT_OPENAI_MODEL,
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
            "enabled": False,
            "urls": [
                "https://www.facebook.com/groups/castingmarseille/",
                "https://www.facebook.com/groups/castingfigurantspaca/",
                "https://www.facebook.com/groups/figurantssud/",
            ],
        },
        "instagram_public": {
            "enabled": False,
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
    if "data_dir" not in cfg or not str(cfg.get("data_dir", "")).strip():
        cfg["data_dir"] = str(APP_DIR)
    if "openai_api_key" not in cfg:
        cfg["openai_api_key"] = ""
    if "openai_model" not in cfg or not str(cfg.get("openai_model", "")).strip():
        cfg["openai_model"] = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
    openai_api_key = str(cfg.get("openai_api_key", "")).strip()
    if not openai_api_key:
        env_openai_api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if env_openai_api_key:
            cfg["openai_api_key"] = env_openai_api_key
    resend_api_key = str(cfg.get("resend_api_key", "")).strip()
    if not resend_api_key or resend_api_key == DEFAULT_CONFIG["resend_api_key"]:
        env_resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()
        if env_resend_api_key:
            cfg["resend_api_key"] = env_resend_api_key
    sender_email = str(cfg.get("sender_email", "")).strip()
    if not sender_email or "votre-domaine.fr" in sender_email or "gmail.com" in sender_email or "googlemail.com" in sender_email or "example.com" in sender_email:
        env_sender_email = os.environ.get("RESEND_SENDER_EMAIL", "").strip()
        if env_sender_email:
            cfg["sender_email"] = env_sender_email
    sender_email = str(cfg.get("sender_email", "")).strip()
    if not sender_email or "votre-domaine.fr" in sender_email or "gmail.com" in sender_email or "googlemail.com" in sender_email or "example.com" in sender_email:
        cfg["sender_email"] = DEFAULT_SENDER_EMAIL
    if "sender_password" in cfg and "resend_api_key" not in cfg:
        cfg["_legacy_gmail_config"] = True
    cfg["_exclude_norm"] = [norm(x) for x in cfg.get("exclude_keywords", [])]
    cfg["_category_norm"] = [norm(x) for x in cfg.get("category_keywords", [])]
    cfg["_zones_norm"] = [norm(x) for x in cfg.get("zones_ok", [])]
    return cfg


def detect_platform() -> str:
    return platform.system().lower()


def config_is_filled(cfg: dict) -> bool:
    return (
        str(cfg.get("resend_api_key", "")).strip() not in ("", DEFAULT_CONFIG["resend_api_key"])
        and str(cfg.get("sender_email", "")).strip() != ""
    )
