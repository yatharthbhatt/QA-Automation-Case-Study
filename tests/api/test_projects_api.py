"""
API-layer tests for project creation and tenant isolation.
These are fast, deterministic, and don't need a browser — ideal for PR gating.
"""
import pytest

from core.base_api import ApiError
from utils.data_factory import new_project

pytestmark = pytest.mark.api


@pytest.mark.smoke
def test_create_project_returns_active(api_client):
    payload = new_project()
    project = api_client.create_project(**payload)

    assert project["id"]
    assert project["name"] == payload["name"]
    assert project["status"] == "active"

    # cleanup (this test doesn't use the created_project fixture because it asserts on creation)
    api_client.delete_project(project["id"])


def test_create_project_rejects_missing_name(api_client):
    """Contract check: the API must reject an invalid payload with a 4xx, not create junk."""
    with pytest.raises(ApiError) as exc:
        api_client.post("/api/v1/projects", json={"description": "no name"}, expected=(201,))
    assert exc.value.response.status_code in (400, 422)


@pytest.mark.security
def test_tenant_cannot_read_other_tenants_project(settings_obj):
    """
    Create a project as company1, then attempt to read it as company2. The platform must deny it
    (403/404). This is the API-level counterpart to the UI tenant-isolation test.
    """
    from api.projects_client import ProjectsClient

    c1 = ProjectsClient(settings_obj.api_base_url, settings_obj.api_token,
                        settings_obj.tenant("company1")["tenant_id"])
    c2 = ProjectsClient(settings_obj.api_base_url, settings_obj.api_token,
                        settings_obj.tenant("company2")["tenant_id"])

    project = c1.create_project(**new_project())
    try:
        status = c2.get_project_status_code(project["id"])
        assert status in (403, 404), (
            f"TENANT ISOLATION BREACH: company2 read company1's project (status {status})"
        )
    finally:
        c1.delete_project(project["id"])
