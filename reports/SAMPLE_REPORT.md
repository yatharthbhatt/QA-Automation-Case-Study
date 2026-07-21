# Sample Test Execution Report (Illustrative)

> **Note:** the target app (`app.workflowpro.com`) is fictional, so this is an *annotated example*
> of the report this framework produces, not output from a live run. Against a real environment,
> `pytest` generates `reports/report.html` (self-contained), `reports/junit.xml`, and
> `reports/artifacts/` (screenshots + Playwright traces on failure) automatically.

---

## Command

```bash
pytest -m "api or integration" --browser-name=chromium --tenant=company1 -n 2 \
       --html=reports/report.html --self-contained-html
```

## Summary (example)

```
============================= test session starts ==============================
platform linux -- Python 3.11.9, pytest-8.2.0, playwright-1.44.0
rootdir: /home/runner/work/workflowpro-qa-automation
plugins: playwright-0.5.0, xdist-3.6.1, html-4.1.1, rerunfailures-14.0
gw0 [6] / gw1 [6]

tests/api/test_projects_api.py::test_create_project_returns_active         PASSED [ 16%]
tests/api/test_projects_api.py::test_create_project_rejects_missing_name   PASSED [ 33%]
tests/api/test_projects_api.py::test_tenant_cannot_read_other_tenants_project PASSED [ 50%]
tests/ui/test_projects_ui.py::test_api_created_project_appears_in_ui        PASSED [ 66%]
tests/integration/...::test_project_creation_flow                          PASSED [ 83%]
tests/integration/...::test_project_accessible_on_mobile                   SKIPPED[100%]
                        (reason: Mobile leg requires --target=browserstack)

======================= 5 passed, 1 skipped in 42.13s ========================
```

## Artifacts produced

| Artifact | Path | Purpose |
|---|---|---|
| HTML report | `reports/report.html` | human-readable, self-contained |
| JUnit XML | `reports/junit.xml` | CI dashboards / trend tracking |
| Failure screenshot | `reports/artifacts/<test>.png` | see the exact failing screen |
| Playwright trace | `reports/artifacts/<test>-trace.zip` | step-by-step replay (`playwright show-trace`) |
| BrowserStack session | dashboard | video + network + device logs (cloud runs) |

## Example failure entry (what a real bug looks like)

```
tests/integration/...::test_project_creation_flow FAILED

    AssertionError: TENANT ISOLATION BREACH at API layer
    company2 read company1's project (status 200)
    >   assert c2_api.get_project_status_code(project_id) in (403, 404)

    Artifacts: reports/artifacts/test_project_creation_flow.png
               reports/artifacts/test_project_creation_flow-trace.zip
```

This is the kind of failure the suite exists to catch — a security-boundary regression, reported
with a precise message and replayable evidence.
