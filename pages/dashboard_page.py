"""DashboardPage — the post-login landing page."""
from __future__ import annotations

from playwright.sync_api import Page, expect

from core.base_page import BasePage


class DashboardPage(BasePage):
    def __init__(self, page: Page, base_url: str):
        super().__init__(page, base_url)
        self.welcome_message = page.locator(".welcome-message")
        self.tenant_badge = page.locator("[data-testid='tenant-name']")

    def expect_loaded(self) -> None:
        """
        Assert we're actually on the dashboard. Uses a web-first assertion so it waits for the
        dashboard to finish its dynamic load rather than checking a value that may not exist yet.
        """
        self.expect_url_contains("/dashboard")
        expect(self.welcome_message).to_be_visible()

    def expect_tenant(self, display_name: str) -> None:
        expect(self.tenant_badge).to_contain_text(display_name)
