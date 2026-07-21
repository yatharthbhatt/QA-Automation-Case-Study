"""ProjectsPage — project list/grid, used for UI verification and tenant-isolation checks."""
from __future__ import annotations

from playwright.sync_api import Page, expect

from core.base_page import BasePage


class ProjectsPage(BasePage):
    def __init__(self, page: Page, base_url: str):
        super().__init__(page, base_url)
        self.cards = page.locator(".project-card")

    def open(self, path: str = "/projects") -> None:
        super().open(path)

    def card_by_name(self, name: str):
        # Scope to the card that contains the exact project name — resilient to ordering/pagination.
        return self.page.locator(".project-card", has_text=name)

    def expect_project_visible(self, name: str) -> None:
        expect(self.card_by_name(name)).to_be_visible()

    def expect_project_absent(self, name: str) -> None:
        """Used in tenant-isolation: the other company's project must NOT render here."""
        expect(self.card_by_name(name)).to_have_count(0)

    def all_card_texts(self) -> list[str]:
        # Wait for at least one card before enumerating, so we never read an empty (still-loading)
        # grid and get a false "isolation passed".
        expect(self.cards.first).to_be_visible()
        return self.cards.all_text_contents()
