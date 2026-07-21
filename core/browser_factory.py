"""
BrowserFactory — one place that knows how to produce a browser context, whether the target is
local (Playwright's bundled browsers) or BrowserStack (cloud web + real mobile).

Tests never touch this directly; the `page` fixture in conftest.py does. That means switching
between local and cloud, or Chrome vs Firefox vs a real iPhone, is a flag change — zero test edits.
"""
from __future__ import annotations

import json
import urllib.parse

from playwright.sync_api import Playwright

from config.config import settings
from utils.logger import get_logger

log = get_logger("browser")

# Map our friendly names to Playwright browser types
_LOCAL_ENGINES = {"chromium": "chromium", "chrome": "chromium",
                  "firefox": "firefox",
                  "webkit": "webkit", "safari": "webkit"}


def launch_local(pw: Playwright, browser_name: str):
    engine = _LOCAL_ENGINES.get(browser_name, "chromium")
    browser_type = getattr(pw, engine)
    log.info("Launching local %s (headless=%s)", engine, settings.headless)
    return browser_type.launch(headless=settings.headless)


def _bstack_cdp_url(caps: dict) -> str:
    caps = {
        **caps,
        "browserstack.username": settings.browserstack_user,
        "browserstack.accessKey": settings.browserstack_key,
        **{k: v for k, v in settings.browserstack.items() if k in ("project", "build")},
    }
    encoded = urllib.parse.quote(json.dumps(caps))
    return f"wss://cdp.browserstack.com/playwright?caps={encoded}"


def connect_browserstack(pw: Playwright, platform: str, profile: str):
    """
    platform: 'web' or 'mobile'; profile: e.g. 'chrome', 'safari', 'android', 'ios'.
    Connects Playwright to a BrowserStack session over CDP.
    """
    caps = settings.browserstack[platform][profile]
    log.info("Connecting to BrowserStack %s/%s", platform, profile)
    return pw.chromium.connect_over_cdp(_bstack_cdp_url(caps))
