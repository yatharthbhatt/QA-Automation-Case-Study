# WorkFlow Pro — QA Automation Framework

A multi-platform (web + mobile + API) test automation framework for a multi-tenant B2B SaaS
project-management platform. Built with **pytest + Playwright + requests + BrowserStack**.

> Submission for the Bynry Inc. QA Automation Engineering case study.
> **Author:** Yatharth Bhatt · **Date:** 21 July 2026

---

## What's in this repo

| Deliverable | Location |
|---|---|
| Test plan | [docs/TEST_PLAN.md](docs/TEST_PLAN.md) |
| Part 1 — Flaky test analysis + fixes | [docs/PART1_FLAKY_TEST_ANALYSIS.md](docs/PART1_FLAKY_TEST_ANALYSIS.md) · code in [tests/part1_login/](tests/part1_login/) |
| Part 2 — Framework design | [docs/PART2_FRAMEWORK_DESIGN.md](docs/PART2_FRAMEWORK_DESIGN.md) |
| Part 3 — API + UI + Mobile integration test | [docs/PART3_INTEGRATION_STRATEGY.md](docs/PART3_INTEGRATION_STRATEGY.md) · code in [tests/integration/](tests/integration/) |
| Testing approach & rationale | [docs/TESTING_APPROACH.md](docs/TESTING_APPROACH.md) |
| Assumptions & open questions | [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md) |
| Sample execution report | [reports/SAMPLE_REPORT.md](reports/SAMPLE_REPORT.md) |

---

## Architecture at a glance

```
config/     → environment + browser + BrowserStack configuration (12-factor, env-driven)
core/       → base classes: BasePage, BaseApiClient, BrowserFactory
pages/      → Page Object Models (LoginPage, DashboardPage, ProjectsPage)
api/        → API service clients (AuthClient, ProjectsClient)
utils/      → data factory, custom waits, logger
data/       → test data (users, tenants, projects) — env-agnostic fixtures
tests/      → the actual tests, grouped by layer (part1_login / api / ui / integration)
conftest.py → shared pytest fixtures (browser, page, api clients, tenant/role, cleanup)
```

The design principle: **tests describe *what* to verify; the framework owns *how*.**
A test never contains a raw selector, a raw URL, or a `sleep()`.

---

## Quick start

### 1. Prerequisites
- Python 3.11+
- Node (Playwright downloads its own browsers, no separate install needed)

### 2. Install
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
playwright install --with-deps
```

### 3. Configure
```bash
cp .env.example .env
# edit .env — set BASE_URL, API creds, and BROWSERSTACK_USERNAME / BROWSERSTACK_ACCESS_KEY
```

### 4. Run

```bash
# Everything (local Chromium, headless)
pytest

# One layer
pytest tests/part1_login
pytest -m api
pytest -m integration

# Pick a browser (local)
pytest --browser-name=firefox
pytest --browser-name=webkit        # Safari engine

# Pick a tenant
pytest --tenant=company2

# Run on BrowserStack (cloud web + real mobile devices)
pytest -m integration --target=browserstack

# Parallel
pytest -n 4

# With HTML report
pytest --html=reports/report.html --self-contained-html
```

---

## How the framework meets the requirements

| Requirement | How it's handled |
|---|---|
| Web: Chrome, Firefox, Safari | `BrowserFactory` + Playwright chromium/firefox/webkit, selected via `--browser-name` |
| Mobile: iOS, Android | BrowserStack real-device capabilities in `config/browserstack.yaml` |
| Multi-tenant | `--tenant` flag → `tenant` fixture resolves URL + `X-Tenant-ID` from `data/tenants.json` |
| Roles (Admin/Manager/Employee) | `role` fixture + `data/users.json`; `@pytest.mark.role("admin")` |
| API testing | `api/` service clients built on `BaseApiClient` (retries, auth, tenant header) |
| BrowserStack | `--target=browserstack` swaps the driver; capabilities set per session |
| CI/CD | [.github/workflows/ci.yml](.github/workflows/ci.yml) — matrix over browser × tenant |

---

## Reporting

- **pytest-html** — self-contained HTML report at `reports/report.html`
- **JUnit XML** — `reports/junit.xml` for CI dashboards
- **Screenshots + trace on failure** — auto-captured via the `page` fixture, saved to `reports/artifacts/`
- **BrowserStack dashboard** — video, network logs, and device logs per session

See [reports/SAMPLE_REPORT.md](reports/SAMPLE_REPORT.md) for an annotated sample.

---

## Key design decisions (short version)

1. **Playwright over Selenium** for web — auto-waiting, built-in tracing, faster and less flaky.
2. **API-first test data setup** — create state via API (fast, reliable), verify via UI. Never
   click through five screens to reach the thing you're actually testing.
3. **Web-first assertions everywhere** (`expect(...).to_be_visible()`) — never `sleep()`, never a
   bare `is_visible()` race. This is the single biggest anti-flake lever (see Part 1).
4. **Everything env-driven** — one codebase runs local, CI, and BrowserStack by changing flags only.
5. **Strict test isolation** — every test gets a fresh browser context (clean cookies/storage) and
   cleans up the data it created.

Full rationale in [docs/TESTING_APPROACH.md](docs/TESTING_APPROACH.md).

---

## Note on runnability

The target app (`app.workflowpro.com`) is fictional, so these tests are written to run against a
real deployment once URLs/credentials are supplied via `.env`. The **structure, patterns, waits,
fixtures, and CI config are production-grade and real**; only the endpoints/selectors would need to
be pointed at an actual environment. Assumptions are documented in
[docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md).
