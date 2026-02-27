#!/usr/bin/env python3
"""VeilleCasting – veille automatique d'annonces de casting."""

import argparse
import hashlib
import json
import logging
import os
import re
import smtplib
import subprocess
import sys
import time
import unicodedata
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
APP_DIR = Path(os.environ.get("APPDATA", ".")) / "VeilleCasting"
CONFIG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "veille.log"
SEEN_FILE = APP_DIR / "seen_hashes.json"

# ---------------------------------------------------------------------------
# Config par defaut
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "sender_email": "VOTRE_GMAIL@gmail.com",
    "sender_password": "VOTRE_MOT_DE_PASSE_APPLICATION_GMAIL_16C",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "recipient_email": "piccinno@hotmail.com",
    "zones_ok": [
        "paca", "provence", "alpes", "cote d'azur", "cote d azur",
        "bouches-du-rhone", "bouches du rhone", "var", "vaucluse",
        "alpes-maritimes", "alpes maritimes", "nice", "marseille",
        "toulon", "avignon", "cannes", "aix-en-provence", "aix en provence",
        "occitanie", "montpellier", "toulouse", "nimes", "perpignan",
        "beziers", "herault", "gard", "aude", "pyrenees-orientales",
        "haute-garonne", "tarn", "ariege", "lot", "aveyron", "gers",
        "tarn-et-garonne", "hautes-pyrenees", "lozere",
        "toute la france", "france entiere", "national"
    ],
    "category_keywords": [
        "figuration", "figurant", "figurante", "casting", "acteur",
        "actrice", "comedien", "comedienne", "doublure", "silhouette",
        "role muet", "extra", "film", "serie", "television", "tv",
        "court-metrage", "court metrage", "long-metrage", "long metrage",
        "publicite", "pub", "clip", "clip video", "theatre", "spectacle"
    ],
    "exclude_keywords": [
        "mannequin", "model", "modele", "photo", "photographe",
        "animateur", "animatrice", "voix off", "voice over",
        "danse", "danseur", "danseuse", "chant", "chanteur", "chanteuse"
    ],
    "sources": {
        "castprod": True,
        "figurants_paca": True,
        "figurants_occitanie": True,
        "occitanie_films": True
    },
    "sleep_between_requests_seconds": 0.7
}

# ---------------------------------------------------------------------------
# Session HTTP avec retries
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def load_config() -> dict:
    cfg = load_json(CONFIG_FILE, None)
    if cfg is None:
        log("Config absente, creation du fichier par defaut.")
        save_json(CONFIG_FILE, DEFAULT_CONFIG)
        cfg = DEFAULT_CONFIG.copy()
    cfg["_exclude_norm"] = [norm(x) for x in cfg.get("exclude_keywords", [])]
    cfg["_category_norm"] = [norm(x) for x in cfg.get("category_keywords", [])]
    cfg["_zones_norm"] = [norm(x) for x in cfg.get("zones_ok", [])]
    return cfg

def config_is_filled(cfg: dict) -> bool:
    return (
        cfg.get("sender_email", "").endswith("@gmail.com")
        and cfg.get("sender_password", "") not in ("", DEFAULT_CONFIG["sender_password"])
    )

# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------
def scrape_castprod(cfg: dict) -> list:
    annonces = []
    base = "https://www.castprod.com"
    empty_pages = 0
    for page in range(1, 11):
        url = f"{base}/annonces/casting?page={page}"
        try:
            r = SESSION.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
        except Exception as e:
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

def scrape_figurants(cfg: dict, region: str) -> list:
    annonces = []
    slug = "provence-alpes-cote-d-azur" if region == "paca" else "occitanie"
    label = "Figurants PACA" if region == "paca" else "Figurants Occitanie"
    base = "https://www.figurants.com"
    url = f"{base}/casting/{slug}"
    try:
        r = SESSION.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
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

def scrape_occitanie_films(cfg: dict) -> list:
    annonces = []
    base = "https://www.occitanie-films.fr"
    url = f"{base}/annonces"
    try:
        r = SESSION.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        log(f"[occitanie-films] Erreur: {e}")
        return annonces
    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select("article, .views-row, .node--type-annonce")
    for item in items:
        title_tag = item.select_one("h2 a, h3 a, .field--name-title a, a")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link = title_tag.get("href", "")
        if link and not link.startswith("http"):
            link = urljoin(base, link)
        desc_tag = item.select_one("p, .field--name-body, .summary")
        desc = desc_tag.get_text(strip=True) if desc_tag else ""
        annonces.append({"title": title, "link": link, "description": desc, "source": "Occitanie Films"})
    if not annonces:
        log("[occitanie-films] ATTENTION: 0 annonce trouvee. Les selecteurs CSS ont peut-etre change.")
    return annonces

# ---------------------------------------------------------------------------
# Filtrage
# ---------------------------------------------------------------------------
def is_relevant(annonce: dict, cfg: dict) -> bool:
    text = norm(annonce.get("title", "") + " " + annonce.get("description", ""))
    for ex in cfg["_exclude_norm"]:
        if ex in text:
            return False
    has_category = any(kw in text for kw in cfg["_category_norm"])
    has_zone = any(z in text for z in cfg["_zones_norm"])
    return has_category or has_zone

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

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
def send_email(cfg: dict, annonces: list) -> bool:
    if not annonces:
        return True
    subject = f"VeilleCasting – {len(annonces)} nouvelle(s) annonce(s) – {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    text_lines = []
    html_rows = []
    for a in annonces:
        text_lines.append(f"- [{a['source']}] {a['title']}\n  {a['link']}")
        html_rows.append(
            f'<tr><td style="padding:6px;border:1px solid #ccc">{a["source"]}</td>'
            f'<td style="padding:6px;border:1px solid #ccc"><a href="{a["link"]}">{a["title"]}</a></td>'
            f'<td style="padding:6px;border:1px solid #ccc">{a.get("description","")[:120]}</td></tr>'
        )
    text_body = "\n".join(text_lines)
    html_body = (
        '<html><body><h2>Nouvelles annonces de casting</h2>'
        '<table style="border-collapse:collapse;font-family:Arial,sans-serif">'
        '<tr style="background:#4a90d9;color:#fff"><th style="padding:8px">Source</th>'
        '<th style="padding:8px">Annonce</th><th style="padding:8px">Description</th></tr>'
        + "".join(html_rows)
        + "</table></body></html>"
    )
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["sender_email"]
    msg["To"] = cfg["recipient_email"]
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    try:
        with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"], timeout=30) as srv:
            srv.starttls()
            srv.login(cfg["sender_email"], cfg["sender_password"])
            srv.sendmail(cfg["sender_email"], cfg["recipient_email"], msg.as_string())
        log(f"Email envoye: {len(annonces)} annonce(s).")
        return True
    except Exception as e:
        log(f"ERREUR envoi email: {e}")
        return False

# ---------------------------------------------------------------------------
# Commandes
# ---------------------------------------------------------------------------
def cmd_init() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        save_json(CONFIG_FILE, DEFAULT_CONFIG)
        log("Config par defaut creee.")
    try:
        subprocess.Popen(["notepad.exe", str(CONFIG_FILE)])
    except Exception:
        log(f"Impossible d'ouvrir Notepad. Editez manuellement : {CONFIG_FILE}")
    log(f"--init termine. Config: {CONFIG_FILE}")

def run_once() -> None:
    log("=== Debut de la veille ===")
    cfg = load_config()
    if not config_is_filled(cfg):
        log("Config non remplie. Lancez --init pour configurer.")
        return
    all_annonces = []
    sources = cfg.get("sources", {})
    if sources.get("castprod", True):
        all_annonces.extend(scrape_castprod(cfg))
    if sources.get("figurants_paca", True):
        all_annonces.extend(scrape_figurants(cfg, "paca"))
        time.sleep(cfg.get("sleep_between_requests_seconds", 0.7))
    if sources.get("figurants_occitanie", True):
        all_annonces.extend(scrape_figurants(cfg, "occitanie"))
        time.sleep(cfg.get("sleep_between_requests_seconds", 0.7))
    if sources.get("occitanie_films", True):
        all_annonces.extend(scrape_occitanie_films(cfg))
    log(f"Total brut: {len(all_annonces)} annonce(s).")
    relevant = [a for a in all_annonces if is_relevant(a, cfg)]
    log(f"Apres filtrage: {len(relevant)} annonce(s) pertinente(s).")
    new = filter_new(relevant)
    log(f"Nouvelles: {len(new)} annonce(s).")
    if new:
        if send_email(cfg, new):
            mark_seen(new)
        else:
            log("Email non envoye, annonces NON marquees comme vues.")
    else:
        log("Aucune nouvelle annonce.")
    log("=== Fin de la veille ===")

# ---------------------------------------------------------------------------
# Point d'entree
# ---------------------------------------------------------------------------
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
    except Exception as e:
        log(f"ERREUR FATALE NON GEREE: {e}")

if __name__ == "__main__":
    main()
