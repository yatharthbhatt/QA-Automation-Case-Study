# Part 2 — Test Automation Framework Design

**Author:** Yatharth Bhatt · **Date:** 21 July 2026

> The framework in this repo *is* the answer to Part 2 — this document explains the design behind it.

---

## 1. Guiding principles

1. **Tests declare *what*; the framework owns *how*.** No test contains a raw selector, URL, or
   `sleep()`. That keeps tests readable and makes app changes a one-place fix (Page Object / config).
2. **One codebase, many targets.** Local / CI / BrowserStack and Chrome / Firefox / Safari / iOS /
   Android are all selected by runtime flags — never by editing test code.
3. **Layered testing.** API, UI, and integration are separate, addressable layers (`pytest -m`).
   Fast API tests gate PRs; heavier UI/mobile runs go nightly.
4. **Isolation + cleanup by default.** Fresh browser context per test; every created entity is
   deleted afterward, even on failure.
5. **Config and secrets are external.** 12-factor: everything env-driven, nothing secret in source.

---

## 2. Folder structure

```
workflowpro-qa-automation/
├── config/                     # HOW to configure a run
│   ├── config.py               #   single source of truth (env + data tables) -> `settings`
│   └── browserstack.yaml       #   web + real-mobile capability profiles
├── core/                       # base classes — the reusable engine
│   ├── base_page.py            #   BasePage: open(), web-first assertion helpers, default timeout
│   ├── base_api.py             #   BaseApiClient: auth + X-Tenant-ID + retry/backoff + errors
│   └── browser_factory.py      #   local vs BrowserStack, engine selection
├── pages/                      # Page Object Models (one per screen)
│   ├── login_page.py           #   includes 2FA handling
│   ├── dashboard_page.py
│   └── projects_page.py
├── api/                        # API service clients (one per backend domain)
│   └── projects_client.py
├── utils/                      # cross-cutting helpers
│   ├── data_factory.py         #   unique, tagged, cleanup-able test data
│   └── logger.py
├── data/                       # environment-agnostic test data / lookup tables
│   ├── tenants.json            #   tenant -> url + X-Tenant-ID
│   ├── users.json              #   tenant x role -> credential source
│   └── test_projects.json
├── tests/                      # the tests, grouped by layer
│   ├── part1_login/            #   Part 1 (original + fixed)
│   ├── api/
│   ├── ui/
│   └── integration/            #   Part 3 flow
├── reports/                    # generated: html, junit, screenshots, traces
├── .github/workflows/ci.yml    # CI matrix: browser x tenant + nightly mobile
├── conftest.py                 # shared fixtures + CLI flags (the control plane)
├── pytest.ini                  # markers, default reporting
└── requirements.txt
```

**Why grouped by layer, not by feature?** Because the *risk profile and run cadence* differ by
layer (API = fast/every-PR, mobile = slow/nightly). Grouping by layer makes `pytest -m` selection
and CI scheduling natural. Within a layer, files map to features/domains.

---

## 3. Base classes & utilities (the reusable core)

- **`BasePage`** — every page object inherits it. Provides `open()`, URL assertions, and sets the
  default timeout centrally. Enforces the "locators + web-first assertions, no sleeps" rule.
- **`BaseApiClient`** — every API client inherits it. Owns the four cross-cutting API concerns:
  Bearer auth, the `X-Tenant-ID` header (critical for multi-tenant), retry-with-backoff on
  *transient* errors only, and consistent error raising/logging.
- **`BrowserFactory`** — the only code that knows local-vs-cloud and which engine/device. Swapping
  targets is a flag.
- **`data_factory`** — generates **unique, tagged** entities so parallel workers and reruns never
  collide, and orphans are identifiable for cleanup.

---

## 4. Configuration management

### Environments (tenants)
`data/tenants.json` maps a short key → `{url, tenant_id, display_name}`. The `--tenant` flag picks
one; the `tenant` fixture resolves it; the API client sends the right `X-Tenant-ID` and the UI hits
the right subdomain. Adding `company3` is a data edit, not a code change.

### Browsers / devices
`--browser-name` (local) and `--bstack-profile` (BrowserStack) select the target;
`config/browserstack.yaml` holds capability profiles. `--target=local|browserstack` decides where.

### Roles & permissions
`data/users.json` maps `tenant → role → credential source` (env-var names, not literal secrets).
A `role` fixture / `@pytest.mark.role("manager")` runs a test as a given role, so permission tests
("Employee cannot delete a project") are first-class.

### Test data
Two kinds, deliberately separated:
- **Reference/fixture data** (`data/*.json`) — stable lookups (tenants, roles), committed.
- **Generated data** (`utils/data_factory.py`) — unique per run, created via API, cleaned up after.

### Secrets
Never in the repo. `.env` locally (git-ignored), a secrets manager / CI secrets in pipelines.
`config.py` is the *only* module that reads the environment.

---

## 5. How each Given Requirement is met

| Requirement | Mechanism |
|---|---|
| Web: Chrome, Firefox, Safari | Playwright chromium/firefox/webkit via `BrowserFactory` + `--browser-name` |
| Mobile: iOS, Android | BrowserStack real devices via `config/browserstack.yaml` + `--bstack-profile` |
| Multiple tenant environments | `data/tenants.json` + `--tenant` + `X-Tenant-ID` header + subdomain routing |
| Roles with varying permissions | `data/users.json` + `role` fixture / `@pytest.mark.role` |
| API testing | `api/` clients on `BaseApiClient`; `pytest -m api` |
| BrowserStack cross-platform | `--target=browserstack`; capabilities per session |
| CI/CD integration | `.github/workflows/ci.yml`: PR smoke gate + nightly browser×tenant matrix + mobile |

---

## 6. Missing requirements — questions I'd ask

Grouped by the areas the brief calls out.

**Test data management**
- Is there a seeded/reset test environment, or do we create-and-clean per run? Is there an API to
  bulk-purge automation data (a nightly janitor) in case a run crashes mid-cleanup?
- Can we get dedicated automation accounts per role per tenant, isolated from manual QA?
- Is production-like data available (volume, PII handling), or synthetic only?

**Reporting & observability**
- Where should results live — Allure, a CI dashboard, Slack alerts? Who consumes them?
- Do we need historical trend/flakiness tracking (e.g. a flaky-test dashboard)?
- What's the on-call/triage process when nightly fails?

**Parallel execution & scale**
- Expected suite size and target wall-clock? (Drives worker count and sharding strategy.)
- Are backends safe for concurrent writes from N parallel workers, or do we need per-worker tenants?

**BrowserStack / cost**
- Parallel-session budget? Which device/browser matrix is *required* vs nice-to-have?
- Do we run the full matrix per PR (expensive) or a small set per-PR + full matrix nightly (my
  default recommendation)?

**Scope / environments**
- Which browsers/devices/OS versions are *actually* in the support matrix (analytics-driven)?
- Do we test staging, production-canary, or both? Any auth differences between them?
- SLA on flakiness (acceptable rerun rate) and on suite runtime for the PR gate?

**Auth**
- Service tokens for API setup (skip UI login)? SSO/2FA specifics for test accounts?

---

## 7. Scalability & maintainability notes (for the live session)

- **Adding a screen** = one Page Object; **adding a backend domain** = one API client; **adding a
  tenant/browser/device** = one data/config edit. Growth is additive, not invasive.
- **Selector strategy:** advocate `data-testid` hooks so tests don't break on styling/copy changes.
- **Sharding:** `pytest-xdist` now; shard across CI runners by test path as the suite grows.
- **Flake control:** web-first assertions everywhere, isolation per test, and a flakiness dashboard
  so we *measure* stability instead of guessing.
