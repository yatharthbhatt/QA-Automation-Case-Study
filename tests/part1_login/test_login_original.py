"""
PART 1 — the ORIGINAL flaky test, kept verbatim for reference and side-by-side comparison.

DO NOT run this in CI. It is included so reviewers can see exactly what was wrong.
The corrected version lives in test_login_fixed.py, and the full analysis is in
docs/PART1_FLAKY_TEST_ANALYSIS.md.

Marked skip so a stray `pytest` never executes it.
"""
import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.skip(reason="Reference copy of the flaky original — see test_login_fixed.py")


def test_user_login():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto("https://app.workflowpro.com/login")

        page.fill("#email", "admin@company1.com")
        page.fill("#password", "password123")
        page.click("#login-btn")

        # FLAW: exact-equality URL check races the redirect; is_visible() doesn't wait.
        assert page.url == "https://app.workflowpro.com/dashboard"
        assert page.locator(".welcome-message").is_visible()

        browser.close()


def test_multi_tenant_access():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto("https://app.workflowpro.com/login")
        page.fill("#email", "user@company2.com")
        page.fill("#password", "password123")
        page.click("#login-btn")

        # FLAW: reads .project-card before the grid has loaded -> often an empty list -> false pass.
        projects = page.locator(".project-card").all()
        for project in projects:
            assert "Company2" in project.text_content()

        browser.close()
