# Testing Approach & Rationale

**Author:** Yatharth Bhatt · **Date:** 21 July 2026

This document explains the *thinking* behind the framework — the "show test framework thinking, not
just individual test cases" the brief asks for.

---

## 1. Philosophy

> A test suite is infrastructure. Its value is trust: a green run must mean the product works, and a
> red run must mean something real broke. Anything that weakens that link — flakiness, false passes,
> hidden state — is a defect in the suite itself.

Three commitments follow from that:

1. **Determinism over speed hacks.** Wait on conditions, never on the clock.
2. **Meaningful failures.** Every failure ships a screenshot/trace and a readable message.
3. **Isolation.** Tests can't depend on order, shared state, or each other's data.

---

## 2. Why these tools

- **Playwright (not Selenium) for web:** auto-waiting locators remove the single biggest source of
  UI flakiness; built-in tracing makes CI failures debuggable; one API drives Chromium, Firefox, and
  WebKit (Safari engine).
- **pytest (not unittest):** fixtures model setup/teardown and dependency injection cleanly; markers
  give us layered selection (`-m api`); parametrization scales data-driven tests.
- **requests + tenacity for API:** explicit, transparent HTTP with retries we control (transient
  only). No hidden magic in the layer where correctness matters most.
- **BrowserStack:** real iOS/Android devices and less-common browsers without owning a device lab.

---

## 3. Anti-flakiness playbook (the core of Part 1, applied everywhere)

| Anti-pattern | What we do instead |
|---|---|
| `time.sleep(n)` | web-first assertions / `wait_for` on a real condition |
| `assert page.url == x` right after click | `expect(page).to_have_url(...)` (auto-retries) |
| `element.is_visible()` as an assertion | `expect(element).to_be_visible()` |
| iterate a locator list immediately | wait for the first item, assert non-empty, then iterate |
| shared login/session across tests | fresh browser context per test |
| hard-coded timeouts per call | one central, env-tunable default |
| retry to "fix" flakiness | fix the wait; reruns are a last resort for external non-determinism |

---

## 4. Multi-tenant testing approach

Multi-tenancy is the platform's defining risk. Our approach:

- **Tenant is a dimension, not a hardcode.** `--tenant` + `data/tenants.json` drive both the UI
  subdomain and the API `X-Tenant-ID`. CI runs the matrix across tenants.
- **Isolation is tested explicitly and often.** Cross-tenant read attempts (API 403/404) and
  cross-tenant UI absence run on every PR — a leak is the worst possible bug here, so it gets the
  fastest feedback loop.
- **Data is tenant-scoped and tagged**, so parallel tenant runs never interfere.

---

## 5. Test data strategy

- **Reference data** (tenants, roles) is committed, stable, and read-only.
- **Transactional data** (projects) is generated per run: unique, tagged `qa-automation`, created
  via API, and deleted in teardown. A nightly janitor sweeps orphans from crashed runs.
- **Secrets** never touch the repo — `.env` locally, CI/secret-manager in pipelines; only
  `config.py` reads the environment.

---

## 6. CI/CD & cost strategy

- **PR gate is fast and cheap:** API + smoke on one browser/tenant. Developers get feedback in
  minutes; BrowserStack minutes aren't burned on every push.
- **Nightly is thorough:** full browser×tenant matrix locally + mobile on BrowserStack.
- **Artifacts on every run:** HTML report, JUnit XML, and failure screenshots/traces are uploaded so
  triage doesn't require re-running.

---

## 7. What I'd add next (roadmap)

1. Role-permission test suite (Admin/Manager/Employee) — framework already supports it.
2. API response-schema validation + UI/API contract tests.
3. Allure reporting + a flakiness/trend dashboard.
4. Visual regression on key mobile screens.
5. Performance smoke (p95 page load) as a separate, non-blocking signal.
