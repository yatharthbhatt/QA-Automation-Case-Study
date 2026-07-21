"""
BasePage — the parent of every Page Object.

Design intent:
- Tests and page objects use Playwright LOCATORS + web-first assertions. Locators auto-wait and
  auto-retry until the element is actionable, which removes the #1 cause of flakiness (see Part 1).
- No page object ever calls time.sleep(). If you think you need a sleep, you actually need a
  condition to wait on — add it here or use expect().
"""
from __future__ import annotations

from playwright.sync_api import Page, expect

from config.config import settings


class BasePage:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.rstrip("/")
        # Applies to all locator actions & expect() calls on this page.
        self.page.set_default_timeout(settings.default_timeout_ms)

    def open(self, path: str = "/") -> None:
        # 'domcontentloaded' + explicit element waits beats 'networkidle', which is unreliable on
        # apps with polling/analytics/websockets that never truly go idle.
        self.page.goto(f"{self.base_url}{path}", wait_until="domcontentloaded")

    def expect_url_contains(self, fragment: str) -> None:
        expect(self.page).to_have_url(lambda url: fragment in url)
