"""
Central configuration.

One rule: nothing in the framework reads os.environ directly except this module.
Everything else imports `settings`. That keeps configuration testable and gives us a single
place to change how config is sourced (env vars today, a secrets manager tomorrow).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()  # loads .env if present; real CI injects env vars directly

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"


def _load_json(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _load_yaml(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv("BASE_URL", "https://app.workflowpro.com")
    api_base_url: str = os.getenv("API_BASE_URL", "https://api.workflowpro.com")
    api_token: str = os.getenv("API_TOKEN", "")
    totp_secret: str = os.getenv("TOTP_SECRET", "")
    headless: bool = os.getenv("HEADLESS", "true").lower() == "true"
    default_timeout_ms: int = int(os.getenv("DEFAULT_TIMEOUT_MS", "15000"))

    browserstack_user: str = os.getenv("BROWSERSTACK_USERNAME", "")
    browserstack_key: str = os.getenv("BROWSERSTACK_ACCESS_KEY", "")

    # Loaded data tables
    tenants: dict = field(default_factory=lambda: _load_json("tenants.json"))
    users: dict = field(default_factory=lambda: _load_json("users.json"))
    browserstack: dict = field(default_factory=lambda: _load_yaml("browserstack.yaml"))

    def tenant(self, key: str) -> dict:
        """Return tenant record (url, tenant_id, display_name) by short key, e.g. 'company1'."""
        try:
            return self.tenants[key]
        except KeyError as exc:
            raise KeyError(f"Unknown tenant '{key}'. Known: {list(self.tenants)}") from exc

    def user(self, tenant_key: str, role: str) -> dict:
        """Return a user record for a given tenant + role."""
        try:
            return self.users[tenant_key][role]
        except KeyError as exc:
            raise KeyError(
                f"No user for tenant='{tenant_key}' role='{role}'."
            ) from exc


settings = Settings()
