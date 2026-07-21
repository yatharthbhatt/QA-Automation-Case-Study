"""
UI-layer test: a project created via API renders correctly in the web UI.
Demonstrates the API-setup / UI-verify pattern in isolation (Part 3 combines the full flow).
"""
import os

import pytest

from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from pages.projects_page import ProjectsPage

pytestmark = pytest.mark.ui


def test_api_created_project_appears_in_ui(page, tenant, created_project):
    login = LoginPage(page, tenant["url"])
    login.open()
    login.login(os.getenv("ADMIN_EMAIL", "admin@company1.com"),
                os.getenv("ADMIN_PASSWORD", "password123"))
    DashboardPage(page, tenant["url"]).expect_loaded()

    projects = ProjectsPage(page, tenant["url"])
    projects.open()
    # Web-first assertion waits for the card to render — no polling, no sleep.
    projects.expect_project_visible(created_project["name"])
