from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


MODULE_NAMES = [
    "veille_casting_app",
    "veille_casting_sources",
    "veille_casting_newsletter",
    "veille_casting_config",
    "veille_casting_audit",
]


def load_modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    for name in MODULE_NAMES:
        sys.modules.pop(name, None)

    app = importlib.import_module("veille_casting_app")
    src = importlib.import_module("veille_casting_sources")
    news = importlib.import_module("veille_casting_newsletter")
    cfg = importlib.import_module("veille_casting_config")
    importlib.import_module("veille_casting_audit")
    return app, src, news, cfg


class DummyResp:
    def __init__(self, text: str = "", payload: dict | None = None):
        self.text = text
        self._payload = payload or {"id": "email_123"}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class DummySession:
    def __init__(self, html: str):
        self.html = html
        self.sent = []

    def mount(self, *args, **kwargs):
        return None

    def get(self, *args, **kwargs):
        return DummyResp(self.html)

    def post(self, url, headers=None, json=None, timeout=None):
        self.sent.append((url, headers, json))
        return DummyResp(payload={"id": "email_123"})


def test_paca_casting_is_classified_and_kept(monkeypatch, tmp_path):
    _, src, news, cfg = load_modules(monkeypatch, tmp_path)

    html = "<html><body><a href='mailto:cast@example.com'>mail</a><div>casting paca marseille H/F 45-60 ans</div></body></html>"
    session = DummySession(html)
    monkeypatch.setattr(src, "extract_contact_value", lambda session, headers, url: ("Email", "cast@example.com"))

    config = cfg.DEFAULT_CONFIG.copy()
    config["_exclude_norm"] = [cfg.norm(x) for x in config["exclude_keywords"]]
    config["_category_norm"] = [cfg.norm(x) for x in config["category_keywords"]]
    config["_zones_norm"] = [cfg.norm(x) for x in config["zones_ok"]]

    item = src._classify_candidate(
        {
            "title": "H/F 45-60 ans pour pub luxe PACA",
            "link": "https://example.com/a",
            "description": "casting paca marseille",
            "source": "CastProd",
        },
        config,
        session,
        {"User-Agent": "test"},
        cfg.AUDIT_FILE,
    )

    assert item is not None
    assert item["classification"] == "CASTING_CONFIRMED"
    assert item["priority"] == "HIGH"
    assert item["region"] == "PACA"
    assert item["contact_method"] == "Email"
    assert item["item_type"] == "pub / campagne"
    assert "mail" in news.build_plain_text_body([item]).lower()


def test_candidate_without_contact_is_rejected(monkeypatch, tmp_path):
    _, src, news, cfg = load_modules(monkeypatch, tmp_path)

    session = DummySession("<html><body>casting paca marseille</body></html>")
    monkeypatch.setattr(src, "extract_contact_value", lambda session, headers, url: None)

    config = cfg.DEFAULT_CONFIG.copy()
    config["_exclude_norm"] = [cfg.norm(x) for x in config["exclude_keywords"]]
    config["_category_norm"] = [cfg.norm(x) for x in config["category_keywords"]]
    config["_zones_norm"] = [cfg.norm(x) for x in config["zones_ok"]]

    item = src._classify_candidate(
        {
            "title": "H/F 45-60 ans pour pub luxe PACA",
            "link": "https://example.com/a",
            "description": "casting paca marseille",
            "source": "CastProd",
        },
        config,
        session,
        {"User-Agent": "test"},
        cfg.AUDIT_FILE,
    )

    assert item is None
    lines = cfg.AUDIT_FILE.read_text(encoding="utf-8").splitlines()
    last = json.loads(lines[-1])
    assert last["keep_or_reject"] == "reject"
    assert last["reject_reason"] == "no_exploitable_contact"
    assert last["source_name"] == "CastProd"


def test_social_public_login_wall_is_unsupported(monkeypatch, tmp_path):
    _, src, news, cfg = load_modules(monkeypatch, tmp_path)

    class BlockedSession:
        def mount(self, *args, **kwargs):
            return None

        def get(self, *args, **kwargs):
            return DummyResp("<html><body>Log in to continue</body></html>")

    monkeypatch.setattr(
        src,
        "social_source_specs",
        lambda cfg: [
            {
                "platform": "facebook",
                "source_name": "Facebook public - https://facebook.com/groups/castingmarseille/",
                "source_url": "https://facebook.com/groups/castingmarseille/",
            }
        ],
    )

    collected = src.collect_social_public(BlockedSession(), {"User-Agent": "test"}, cfg.DEFAULT_CONFIG, lambda msg: None)

    assert collected == []
    lines = cfg.AUDIT_FILE.read_text(encoding="utf-8").splitlines()
    last = json.loads(lines[-1])
    assert last["keep_or_reject"] == "reject"
    assert last["reject_reason"] == "unsupported_source_or_login_wall"
    assert last["source_type"] == "social public"
