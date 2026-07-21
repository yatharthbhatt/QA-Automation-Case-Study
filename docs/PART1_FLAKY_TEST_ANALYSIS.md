# Part 1 — Debugging the Flaky Login Test

**Author:** Yatharth Bhatt · **Date:** 21 July 2026

Original code: [tests/part1_login/test_login_original.py](../tests/part1_login/test_login_original.py)
Fixed code: [tests/part1_login/test_login_fixed.py](../tests/part1_login/test_login_fixed.py)

---

## 1. Flakiness issues (full list)

| # | Issue | Where | Severity |
|---|---|---|---|
| 1 | **Exact URL equality** `assert page.url == ".../dashboard"` checked immediately after click. The click returns before the redirect + SPA route settles, so `page.url` is often still `/login`. | both tests | High |
| 2 | **`is_visible()` doesn't wait.** It returns the element's visibility *right now*. On a dashboard with dynamic loading, `.welcome-message` usually isn't in the DOM yet → returns `False`. | `test_user_login` | High |
| 3 | **Reading `.project-card` before the grid loads.** `locator(...).all()` snapshots whatever exists at that instant. The grid is fetched async, so the list is frequently **empty** → the `for` loop runs zero times → the test **passes without verifying anything** (false pass — worse than a failure). | `test_multi_tenant_access` | Critical |
| 4 | **No 2FA handling.** Some accounts require a 2FA code. If the test account ever gets 2FA enabled, login silently never completes and every downstream assertion flakes. | both | High |
| 5 | **No error handling / diagnostics.** No screenshot, trace, or clear message on failure — in CI you get "assert False" with no context, so it's impossible to tell a real bug from an env blip. | both | Medium |
| 6 | **Hard-coded URLs, emails, passwords.** Can't switch tenant/env; a rotated password breaks the suite; secrets live in source. | both | Medium |
| 7 | **No default timeout tuned for slow tenants.** "Different tenants have different loading times," but every wait uses library defaults. Slow tenants intermittently exceed them. | both | Medium |
| 8 | **Repeated boilerplate** (`sync_playwright()`, launch, close in every test). Any lifecycle mistake (e.g. a missed `close()` on failure) leaks browsers in CI and destabilises later tests. | both | Low |
| 9 | **No isolation between tests.** Nothing guarantees a clean session/storage state; state bleed between tests causes order-dependent flakiness. | both | Medium |
| 10 | **`assert` on a bare boolean instead of a web-first assertion** — even where waiting exists, a plain `assert` gives no retry and no readable diff. | both | Low |

---

## 2. Root causes — why CI fails but local "works"

The common thread is **implicit timing assumptions that only hold on a fast, warm machine.**

- **Timing / async rendering (issues 1–3).** Locally the app is often cached, the network is fast,
  and the machine is idle, so the redirect and the async grid finish within milliseconds — the race
  is *usually* won. CI is slower and noisier: cold caches, shared CPU, containerised network,
  parallel jobs. The same race is now *usually lost*, so failures appear "randomly."
- **Environment variance (issues 4, 6, 7).** CI runs across "different browsers and screen sizes"
  and against tenants with "different loading times." Hard-coded values and default timeouts that
  fit one fast local combo don't fit all CI combos.
- **False passes (issue 3)** hide until someone notices coverage is fake — the multi-tenant test
  passing on an empty grid is a *silent* failure that CI can't even flag.
- **No isolation / diagnostics (5, 8, 9).** Local runs are one-at-a-time and observable; CI runs
  parallel and headless, so state bleed and resource leaks surface there, and the lack of artifacts
  makes them near-impossible to debug.

**One-line summary:** the tests encode "the app is instant," which is true locally and false in CI.

---

## 3. The fixes (principles → concrete changes)

### Principle: replace timing assumptions with explicit conditions.
Playwright **locators + web-first assertions auto-wait and auto-retry** until the condition is true
or the timeout expires. This single change kills issues 1, 2, 3, 10.

```python
# Before (races):
assert page.url == "https://app.workflowpro.com/dashboard"
assert page.locator(".welcome-message").is_visible()

# After (waits, retries, readable failure):
expect(page).to_have_url(lambda url: "/dashboard" in url)
expect(page.locator(".welcome-message")).to_be_visible()
```

### Principle: never assert over a possibly-empty collection.
```python
texts = projects.all_card_texts()   # waits for the FIRST card to be visible before reading
assert texts, "grid was empty"      # empty grid now FAILS loudly instead of passing silently
for text in texts:
    assert company2_name in text
```

### Principle: handle 2FA deterministically.
Automation accounts share a TOTP secret; we compute the current code instead of hand-typing one.
The login flow detects the OTP field and only fills it when present, so 2FA and non-2FA accounts
both work.
```python
login.login(email, password, totp_code=pyotp.TOTP(settings.totp_secret).now())
```

### Principle: config over hard-coding.
URLs, emails, passwords, timeouts come from `.env`/config. Switching tenant or environment is a
flag, and secrets never live in source.

### Principle: isolation + diagnostics for free.
The `page` fixture gives every test a **fresh browser context** (clean cookies/storage) and, on
failure, saves a **screenshot + Playwright trace** to `reports/artifacts/`. Browser lifecycle lives
in fixtures, so no test can leak a browser.

### On retries (`pytest-rerunfailures`)
We include it but treat it as a **last resort for genuinely non-deterministic externalities**
(e.g. a third-party integration), never as a way to paper over a real race. Fixing the wait is
always preferred; a test that needs reruns to pass is a bug report, not a solution.

The corrected tests are in
[tests/part1_login/test_login_fixed.py](../tests/part1_login/test_login_fixed.py).

---

## 4. Clarifying questions I'd ask (from the "you may need to ask for more" hint)

1. Are the automation test accounts 2FA-enabled? If so, can we provision a shared TOTP secret (or a
   test-only bypass) so codes are deterministic?
2. Is there a stable hook for "dashboard fully loaded" (e.g. a `data-testid="dashboard-ready"`
   element or a network response) I can wait on, rather than the welcome message?
3. What are realistic p95 load times per tenant, so I can set timeouts that are generous but still
   catch real regressions?
4. Are `#email`, `#login-btn`, `.project-card` stable, or should we add `data-testid` attributes?
   (Test-only attributes are the most robust selectors.)
5. Is there an API/service token for test accounts so setup/auth can skip the UI where possible?
