"""API service client for the Projects domain. Maps 1:1 to backend endpoints."""
from __future__ import annotations

from core.base_api import BaseApiClient


class ProjectsClient(BaseApiClient):
    def create_project(self, name: str, description: str = "", team_members=None) -> dict:
        """POST /api/v1/projects -> {"id", "name", "status"}"""
        body = {"name": name, "description": description, "team_members": team_members or []}
        return self.post("/api/v1/projects", json=body).json()

    def get_project(self, project_id: int, expected=(200,)) -> dict:
        return self.get(f"/api/v1/projects/{project_id}", expected=expected).json()

    def list_projects(self) -> list[dict]:
        return self.get("/api/v1/projects").json()

    def delete_project(self, project_id: int) -> None:
        """Used by cleanup fixtures. Idempotent-ish: a 404 on cleanup is acceptable."""
        self.delete(f"/api/v1/projects/{project_id}", expected=(200, 204, 404))

    def get_project_status_code(self, project_id: int) -> int:
        """
        Raw status probe used by tenant-isolation tests: we WANT to see the 403/404 that proves
        another tenant cannot read this project, so we don't raise on those.
        """
        resp = self.get(f"/api/v1/projects/{project_id}", expected=(200, 403, 404))
        return resp.status_code
