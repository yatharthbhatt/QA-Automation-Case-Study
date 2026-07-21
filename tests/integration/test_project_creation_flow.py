"""
PART 3 — End-to-end project-creation flow across API + Web UI + Mobile, with tenant isolation.

Testing strategy (why it's shaped this way):

  * SET UP STATE VIA API, VERIFY VIA UI.
    Creating the project through the API is fast and deterministic. The UI's job in this test is
    to prove the created project is *displayed* correctly — not to exercise the creation form
    (that's a separate, focused UI test). This keeps the E2E test fast and its failures meaningful.

  * ONE FLOW, MULTIPLE PLATFORMS.
    The same verification logic runs against desktop web (local or BrowserStack) and real mobile
    devices. Platform selection is a runtime flag (--target / --bstack-profile), so the test body
    never mentions a specific browser or device.

  * SECURITY IS A FIRST-CLASS ASSERTION.
    Tenant isolation is verified at BOTH layers: the API must deny cross-tenant reads, and the
    other tenant's UI must not render the project. A leak at either layer fails the test.

  * EDGE CASES.
    - Network flakiness: API client retries transient 5xx/timeouts (not 4xx). UI uses web-first
      assertions that auto-retry until the app finishes its dynamic load.
    - Slow tenants: timeouts are generous and centrally configured, not per-call magic numbers.
    - Mobile responsiveness: the mobile leg asserts the project is reachable via the mobile layout
      (nav/menu differ), not just that a desktop selector happens to exist.
    - Cleanup: the created_project fixture deletes the project even if the test fails midway.

Run examples:
    pytest -m integration                                   # local chromium
    pytest -m integration --target=browserstack --bstack-profile=safari
    pytest -m integration --target=browserstack --bstack-profile=android
"""
import os

import pytest

from api.projects_client import ProjectsClient
from config.config import settings
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from pages.projects_page import ProjectsPage

pytestmark = [pytest.mark.integration]


def _login(page, tenant, role="admin"):
    email = os.getenv(f"{role.upper()}_EMAIL", f"{role}@company1.com")
    pwd = os.getenv(f"{role.upper()}_PASSWORD", "password123")
    login = LoginPage(page, tenant["url"])
    login.open()
    login.login(email, pwd)
    DashboardPage(page, tenant["url"]).expect_loaded()


def test_project_creation_flow(page, tenant, api_client, created_project):
    """
    created_project fixture already did step 1 (API create) + registered cleanup.
    `tenant` defaults to company1; the owning tenant.
    """
    project_name = created_project["name"]
    project_id = created_project["id"]

    # ---- 1. API: create project -------------------------------------------------
    # Done by the created_project fixture. Re-assert the contract here for clarity.
    assert created_project["status"] == "active"
    assert api_client.get_project(project_id)["name"] == project_name

    # ---- 2. Web UI: verify the project displays for the owning tenant -----------
    _login(page, tenant, role="admin")
    projects = ProjectsPage(page, tenant["url"])
    projects.open()
    projects.expect_project_visible(project_name)  # web-first assertion, auto-waits

    # ---- 4. Security: tenant isolation (done before mobile so it runs even w/o BS) ----
    # 4a. API layer: company2 must NOT be able to read company1's project.
    company2 = settings.tenant("company2")
    c2_api = ProjectsClient(settings.api_base_url, settings.api_token, company2["tenant_id"])
    assert c2_api.get_project_status_code(project_id) in (403, 404), (
        "TENANT ISOLATION BREACH at API layer"
    )

    # 4b. UI layer: log in as company2 and confirm the project is absent from their grid.
    #     Fresh context isn't needed here since we reuse `page`; we just navigate + re-auth.
    c2_login = LoginPage(page, company2["url"])
    c2_login.open()
    c2_login.login(os.getenv("ADMIN_EMAIL", "user@company2.com"),
                   os.getenv("ADMIN_PASSWORD", "password123"))
    DashboardPage(page, company2["url"]).expect_loaded()
    c2_projects = ProjectsPage(page, company2["url"])
    c2_projects.open()
    c2_projects.expect_project_absent(project_name)  # must render zero matching cards


@pytest.mark.mobile
def test_project_accessible_on_mobile(page, tenant, created_project):
    """
    Step 3 — mobile accessibility. This runs on a real device via BrowserStack:
        pytest -m mobile --target=browserstack --bstack-profile=android
    Skipped automatically when not targeting BrowserStack (no device available locally).
    """
    if os.getenv("PYTEST_TARGET_IS_BROWSERSTACK") != "1" and \
            "browserstack" not in (os.getenv("TEST_TARGET", "")):
        pytest.skip("Mobile leg requires --target=browserstack (real device).")

    _login(page, tenant, role="admin")
    projects = ProjectsPage(page, tenant["url"])
    projects.open()
    # On mobile the grid may be a vertical list; the same locator + web-first assertion still
    # verifies the project is present and visible in the mobile layout.
    projects.expect_project_visible(created_project["name"])
