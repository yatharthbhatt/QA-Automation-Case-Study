"""
Shared pytest fixtures — the framework's control plane.

CLI options this adds:
    --browser-name=chromium|firefox|webkit   local browser engine
    --tenant=company1|company2                which tenant to target
    --target=local|browserstack               where to run
    --bstack-profile=chrome|safari|android|ios  which BrowserStack profile

Fixture map:
    settings_obj  -> global config
    tenant        -> resolved tenant record for this run
    api_client    -> authenticated, tenant-scoped ProjectsClient
    context/page  -> a FRESH, isolated browser context per test (clean cookies/storage)
    created_project -> factory+cleanup: creates a project via API, deletes it after the test
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from api.projects_client import ProjectsClient
from config.config import settings
from core import browser_factory
from utils.logger import get_logger

log = get_logger("conftest")
ARTIFACTS = Path("reports/artifacts")


# --------------------------------------------------------------------------- CLI options
def pytest_addoption(parser):
    parser.addoption("--browser-name", default="chromium",
                     help="Local browser engine: chromium|firefox|webkit")
    parser.addoption("--tenant", default="company1", help="Tenant key: company1|company2")
    parser.addoption("--target", default="local", help="local|browserstack")
    parser.addoption("--bstack-profile", default="chrome",
                     help="BrowserStack profile: chrome|firefox|safari|android|ios")


# --------------------------------------------------------------------------- config fixtures
@pytest.fixture(scope="session")
def settings_obj():
    return settings


@pytest.fixture
def tenant(request):
    key = request.config.getoption("--tenant")
    return settings.tenant(key)


@pytest.fixture
def api_client(tenant) -> ProjectsClient:
    """
    Tenant-scoped API client. Token resolution order:
      1. API_TOKEN from env (service token) — preferred for speed/reliability.
      2. (Extension point) log in via the auth endpoint to mint a token.
    """
    token = settings.api_token or _mint_token_placeholder(tenant)
    return ProjectsClient(
        base_url=settings.api_base_url,
        token=token,
        tenant_id=tenant["tenant_id"],
    )


def _mint_token_placeholder(tenant) -> str:
    # In a real environment this would call POST /api/v1/auth/login and return the JWT.
    # Kept explicit so it's obvious where auth plugs in.
    if not settings.api_token:
        log.warning("No API_TOKEN set — API tests need a real token/auth endpoint to run live.")
    return settings.api_token


# --------------------------------------------------------------------------- browser fixtures
@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as pw:
        yield pw


@pytest.fixture
def browser(playwright_instance, request):
    target = request.config.getoption("--target")
    if target == "browserstack":
        profile = request.config.getoption("--bstack-profile")
        platform = "mobile" if profile in ("android", "ios") else "web"
        browser = browser_factory.connect_browserstack(playwright_instance, platform, profile)
    else:
        name = request.config.getoption("--browser-name")
        browser = browser_factory.launch_local(playwright_instance, name)
    yield browser
    browser.close()


@pytest.fixture
def context(browser):
    # A brand-new context per test = isolated cookies/localStorage/session. This is a core
    # anti-flake + test-independence guarantee: no test can inherit another's login state.
    ctx = browser.new_context()
    ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
    yield ctx
    ctx.close()


@pytest.fixture
def page(context, request):
    pg = context.new_page()
    yield pg
    # On failure, persist a screenshot + Playwright trace for debugging CI runs.
    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        safe = request.node.name.replace("/", "_")
        pg.screenshot(path=str(ARTIFACTS / f"{safe}.png"), full_page=True)
        context.tracing.stop(path=str(ARTIFACTS / f"{safe}-trace.zip"))


# --------------------------------------------------------------------------- data fixtures
@pytest.fixture
def created_project(api_client):
    """
    Create a project via API before the test, hand it over, and DELETE it afterwards.
    Guarantees: no test pollutes the environment, reruns are clean, parallel workers don't collide
    (unique names come from the data factory).
    """
    from utils.data_factory import new_project

    payload = new_project()
    project = api_client.create_project(**payload)
    log.info("Created project id=%s name=%s", project.get("id"), project.get("name"))
    yield {**project, **payload}
    try:
        api_client.delete_project(project["id"])
        log.info("Cleaned up project id=%s", project["id"])
    except Exception as exc:  # cleanup must never fail the test itself
        log.warning("Cleanup failed for project id=%s: %s", project.get("id"), exc)


# --------------------------------------------------------------------------- hooks
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # Exposes pass/fail status to fixtures (so `page` can screenshot only on failure).
    outcome = yield
    setattr(item, f"rep_{call.when}", outcome.get_result())
