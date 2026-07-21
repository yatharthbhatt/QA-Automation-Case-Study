"""
Test-data factory.

Why a factory instead of static JSON for created entities:
- Every run needs UNIQUE names so parallel workers and reruns don't collide, and so a leftover
  project from a crashed run never causes a false pass/fail.
- We tag generated data with a run id + 'qa-automation' so cleanup can find and delete orphans.
"""
from __future__ import annotations

import time
import uuid


def unique_suffix() -> str:
    """Short, sortable, collision-resistant suffix for entity names."""
    return f"{int(time.time())}-{uuid.uuid4().hex[:6]}"


def new_project(name_prefix: str = "QA Project", **overrides) -> dict:
    """Build a project payload with a guaranteed-unique name.

    The 'qa-automation' marker in the description lets the cleanup routine (and a nightly
    janitor job) identify and purge anything this framework created.
    """
    payload = {
        "name": f"{name_prefix} {unique_suffix()}",
        "description": "qa-automation | safe to delete",
        "team_members": [],
    }
    payload.update(overrides)
    return payload
