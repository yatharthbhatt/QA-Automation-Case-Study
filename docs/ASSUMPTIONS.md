# Assumptions & Open Questions

**Author:** Yatharth Bhatt · **Date:** 21 July 2026

The brief states requirements are "intentionally incomplete" and rewards recognising that. Below are
the assumptions I made to produce a complete, coherent submission, and the questions I'd resolve
with the team before this ran against a real environment.

---

## 1. Assumptions made

### Application / environment
- `app.workflowpro.com` is fictional; tests are written to run against a real deployment once URLs
  and credentials are supplied via `.env`. Structure, waits, fixtures, and CI are production-grade.
- Tenants are addressed by subdomain (`company1.workflowpro.com`) **and** an `X-Tenant-ID` header on
  the API — both are honoured by the framework.
- The dashboard exposes a stable "ready" signal (we use `.welcome-message`; ideally a `data-testid`).

### Authentication
- Automation test accounts exist **per role, per tenant**, isolated from manual QA.
- An API **service token** (`API_TOKEN`) is available so API setup can skip UI login. If not, the
  `_mint_token_placeholder` hook in `conftest.py` marks exactly where a login-endpoint call plugs in.
- 2FA on automation accounts (if enabled) uses a **shared TOTP secret** so codes are deterministic.

### API contract (from the brief)
- `POST /api/v1/projects` returns `{"id", "name", "status": "active"}`.
- Cross-tenant reads return **403 or 404** — the security assertions verify exactly this.
- A `DELETE /api/v1/projects/{id}` endpoint exists for cleanup (assumed; used by teardown).

### Selectors
- `#email`, `#password`, `#login-btn`, `.welcome-message`, `.project-card` are current and stable.
  In practice I'd request dedicated `data-testid` attributes.

### Test data
- Creating and deleting projects via API in a shared test environment is acceptable.
- A nightly janitor can purge anything tagged `qa-automation` if a run crashes mid-cleanup.

### Mobile
- BrowserStack credentials and sufficient parallel-session capacity are available in CI.
- Mobile web (responsive) is in scope; native apps are **not** (would need Appium).

---

## 2. Open questions I'd ask (prioritised)

**Blocking for a live run**
1. What are the real base URLs (staging vs prod-canary) and where do test credentials come from?
2. Is there an API service token, or must API tests authenticate via the login endpoint?
3. Are automation accounts 2FA-enabled? Can we get a shared TOTP secret or a test-only bypass?

**Important for reliability**
4. Is there a stable "app ready" hook to wait on? Can we add `data-testid` attributes?
5. What are realistic p95 load times per tenant (to tune timeouts)?
6. Is the backend safe for concurrent writes from N parallel workers, or do we need per-worker data?

**Important for scope/cost**
7. What's the *required* browser/device/OS support matrix (analytics-driven)?
8. BrowserStack parallel-session budget? Full matrix per-PR or nightly-only?
9. Where should reports live (Allure, dashboard, Slack) and who triages nightly failures?

**Nice to have**
10. Are there bulk test-data setup/reset APIs?
11. What's the acceptable flakiness SLA and PR-gate runtime budget?

---

## 3. Things I deliberately did NOT do (and why)

- **No hard-coded secrets or URLs** — everything is env-driven; committing them would be a security
  and maintainability defect.
- **No `sleep()` anywhere** — see the anti-flakiness playbook in TESTING_APPROACH.md.
- **Did not fake a green run** — the sample report is clearly labelled illustrative, since the target
  app doesn't exist yet.
