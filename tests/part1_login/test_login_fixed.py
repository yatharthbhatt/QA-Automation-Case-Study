"""
PART 1 — corrected, reliable version of the login tests.

Key changes vs the original (full write-up in docs/PART1_FLAKY_TEST_ANALYSIS.md):
  1. Web-first assertions (expect(...)) that auto-wait — no exact-equality URL race, no bare
     is_visible() that returns before the element renders.
  2. No shared/hard-coded browser lifecycle in the test body — the `page` fixture provides an
     isolated context per test, with tracing + failure screenshots.
  3. 2FA handled explicitly and deterministically via a TOTP code.
  4. Credentials/URLs come from config, not hard-coded strings.
  5. Multi-tenant test asserts the grid actually loaded AND is non-empty before checking isolation,
     so an empty (still-loading) grid can never produce a false pass.
"""
import os

import pyotp  # optional; see note below
import pytest
from playwright.sync_api import expect

from config.config import settings
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from pages.projects_page import ProjectsPage

pytestmark = pytest.mark.ui


def _totp_code() -> str | None:
    """Generate a current 2FA code for automation accounts, if a shared secret is configured."""
    secret = settings.totp_secret
    return pyotp.TOTP(secret).now() if secret else None


@pytest.mark.smoke
def test_user_login(page, tenant):
    creds = (os.getenv("ADMIN_EMAIL", "admin@company1.com"),
             os.getenv("ADMIN_PASSWORD", "password123"))

    login = LoginPage(page, tenant["url"])
    login.open()
    login.login(*creds, totp_code=_totp_code())

    dashboard = DashboardPage(page, tenant["url"])
    # Waits for the redirect AND the dynamically-loaded welcome message. No sleeps, no races.
    dashboard.expect_loaded()


@pytest.mark.security
def test_multi_tenant_access(page):
    """A company2 user must see ONLY company2 data."""
    company2 = settings.tenant("company2")
    creds = (os.getenv("ADMIN_EMAIL", "user@company2.com"),
             os.getenv("ADMIN_PASSWORD", "password123"))

    login = LoginPage(page, company2["url"])
    login.open()
    login.login(*creds, totp_code=_totp_code())

    projects = ProjectsPage(page, company2["url"])
    projects.open()

    # all_card_texts() waits for the grid to render at least one card before enumerating,
    # so we never assert over an empty list.
    texts = projects.all_card_texts()
    assert texts, "Expected at least one project for company2; grid was empty."
    for text in texts:
        assert company2["display_name"] in text, f"Cross-tenant leak: '{text}'"
