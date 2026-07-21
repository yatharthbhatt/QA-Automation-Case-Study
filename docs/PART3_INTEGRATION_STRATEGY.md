# Part 3 — API + UI + Mobile Integration Test

**Author:** Yatharth Bhatt · **Date:** 21 July 2026

Test code: [tests/integration/test_project_creation_flow.py](../tests/integration/test_project_creation_flow.py)

---

## 1. What the test validates

The complete project-creation flow, end to end:

1. **API** — create a project (`POST /api/v1/projects` with `Authorization` + `X-Tenant-ID`).
2. **Web UI** — the project renders correctly for the owning tenant.
3. **Mobile** — the project is reachable on a real mobile device (BrowserStack).
4. **Security** — tenant isolation holds at **both** the API and UI layers.

---

## 2. Testing strategy & key decisions

### Set up state via API, verify via UI
Creating the project through the API is fast and deterministic. Driving the creation *form* through
the UI would make this E2E test slow and give it two reasons to fail (form bugs vs display bugs).
So the API creates; the UI's job here is purely to prove correct **display**. (A separate, focused
UI test covers the creation form itself.)

### One flow, many platforms — no test edits
The same verification runs on desktop web (local or BrowserStack) and real mobile, chosen by
`--target` / `--bstack-profile`. The test body never names a browser or device.

### Security is a first-class assertion, checked at two layers
Tenant isolation is the highest-risk property of a multi-tenant SaaS, so we verify it twice:
- **API:** company2's client requests company1's project id → must get **403/404**.
- **UI:** logged in as company2 → the project must be **absent** from their grid.
A leak at *either* layer fails the test. (We assert on the *status code*, deliberately not raising,
so the isolation check can observe the denial rather than crashing on it.)

### Data lifecycle
The `created_project` fixture creates the project (unique, tagged name) **before** the test and
**deletes it after — even if the test fails midway**. No environment pollution, clean reruns, no
cross-worker collisions.

---

## 3. Handling test data across API + UI

- **Single source of the entity:** the project is created once, via API, in a fixture. The UI and
  mobile legs both reference the *same* returned `id`/`name`. There is no risk of the API and UI
  testing different data.
- **Uniqueness:** names carry a timestamp + random suffix (`utils/data_factory.py`) so parallel
  runs and reruns never clash.
- **Discoverability for cleanup:** every generated entity is tagged `qa-automation` in its
  description, so a nightly janitor can purge orphans from crashed runs.
- **Credentials/tenants:** resolved from config per tenant/role, never hard-coded.

---

## 4. Cross-platform validation

| Platform | How |
|---|---|
| Chrome / Firefox / Safari (desktop) | `--browser-name` locally, or BrowserStack web profiles |
| Android / iOS (real devices) | `--target=browserstack --bstack-profile=android|ios` |

The mobile leg (`test_project_accessible_on_mobile`) is marked `@pytest.mark.mobile` and **skips
automatically** when not targeting BrowserStack, since there's no real device locally. On mobile the
layout differs (list vs grid, hamburger nav), but the same locator + web-first assertion verifies
presence in the mobile layout — we assert *reachability in the real mobile UI*, not that a desktop
selector coincidentally exists.

---

## 5. Edge cases handled

| Edge case | Handling |
|---|---|
| Transient network failure (API) | `BaseApiClient` retries 5xx/timeouts with exponential backoff; **never** retries 4xx (those are real findings). |
| Slow / variable tenant load (UI) | Web-first assertions auto-retry until the app finishes its dynamic load; timeouts are central and generous, not per-call magic numbers. |
| Async grid not yet rendered | `ProjectsPage` waits for the first card before enumerating — no false pass on an empty grid. |
| Mobile responsiveness | Dedicated mobile leg on a real device; asserts against the mobile layout. |
| Test crashes mid-run | Cleanup runs in fixture teardown regardless of outcome; cleanup failures are logged, never mask the test result. |
| Debugging CI failures | Screenshot + Playwright trace saved on failure; BrowserStack video/logs for cloud runs. |
| Flaky externalities | `pytest-rerunfailures` available as a *last resort*, not a crutch. |

---

## 6. Assumptions (see also docs/ASSUMPTIONS.md)

- **Auth:** an API service token (`API_TOKEN`) exists for test accounts; otherwise the framework
  has an explicit extension point to mint a token via the login endpoint.
- **Tenant header:** the backend enforces isolation on `X-Tenant-ID` and returns 403/404 for
  cross-tenant reads (this is exactly what the security assertion verifies).
- **Selectors:** `.project-card`, `.welcome-message`, `#email/#password/#login-btn` are stable; I'd
  push for `data-testid` hooks in reality.
- **Cleanup:** a `DELETE /api/v1/projects/{id}` endpoint exists and is safe for test data.
- **Mobile:** BrowserStack credentials and parallel-session capacity are available in CI.

---

## 7. If I had more time / production hardening

- API-level **response schema validation** (pydantic/jsonschema) on the create response.
- A **contract test** so UI and API can't silently drift on field names.
- **Visual regression** on the project card (Playwright screenshots) for the mobile layout.
- A **flakiness dashboard** feeding off the JUnit history to catch regressions in stability itself.
