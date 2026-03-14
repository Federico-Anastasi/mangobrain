"""MangoBrain — Setup progress tests.

Run: python -m pytest tests/test_setup.py -v
"""

from __future__ import annotations

import asyncio
import os
import sys

import numpy as np
import pytest

# Ensure server package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
async def db():
    """Create a test database with setup_progress table."""
    from server.database import Database
    test_path = "data/test_setup.db"
    Database._instance = None  # Reset singleton
    database = await Database.create(test_path)
    yield database
    await database.close()
    Database._instance = None
    if os.path.exists(test_path):
        os.remove(test_path)


@pytest.mark.asyncio
async def test_init_setup_progress(db):
    """Test initializing setup steps for a project."""
    count = await db.init_setup_progress("testproject")
    assert count == 14  # 14 steps defined in SETUP_STEPS_TEMPLATE

    # Second call should not create duplicates
    count2 = await db.init_setup_progress("testproject")
    assert count2 == 0


@pytest.mark.asyncio
async def test_get_setup_progress(db):
    """Test retrieving setup steps."""
    await db.init_setup_progress("testproject")
    steps = await db.get_setup_progress("testproject")

    assert len(steps) == 14
    assert steps[0].phase == "install"
    assert steps[0].step == "skills_rules"
    assert steps[0].order_index == 1
    assert steps[-1].phase == "ready"
    assert steps[-1].step == "memory_ready"

    # All should be pending
    from server.models import SetupStatus
    assert all(s.status == SetupStatus.pending for s in steps)


@pytest.mark.asyncio
async def test_update_setup_step(db):
    """Test updating a step's status."""
    await db.init_setup_progress("testproject")

    ok = await db.update_setup_step("testproject", "install", "skills_rules", {
        "status": "completed",
    })
    assert ok

    steps = await db.get_setup_progress("testproject")
    assert steps[0].status.value == "completed"


@pytest.mark.asyncio
async def test_get_setup_summary(db):
    """Test the summary computation."""
    await db.init_setup_progress("testproject")

    summary = await db.get_setup_summary("testproject")
    assert summary["initialized"] is True
    assert summary["total_steps"] == 14
    assert summary["completed"] == 0
    assert summary["progress_pct"] == 0
    assert summary["is_ready"] is False
    assert summary["current_step"] is not None
    assert summary["current_step"]["phase"] == "install"

    # Complete a step
    await db.update_setup_step("testproject", "install", "skills_rules", {"status": "completed"})
    summary = await db.get_setup_summary("testproject")
    assert summary["completed"] == 1
    assert summary["progress_pct"] == 7  # 1/14 ≈ 7%


@pytest.mark.asyncio
async def test_summary_nonexistent_project(db):
    """Test summary for a project that doesn't exist."""
    summary = await db.get_setup_summary("nonexistent")
    assert summary["initialized"] is False


@pytest.mark.asyncio
async def test_multiple_projects(db):
    """Test setup for multiple projects."""
    await db.init_setup_progress("project_a")
    await db.init_setup_progress("project_b")

    all_projects = await db.get_all_projects_setup()
    assert len(all_projects) == 2
    names = {p["project"] for p in all_projects}
    assert names == {"project_a", "project_b"}


def test_config_loading():
    """Test that config values are loaded correctly."""
    from server.config import (
        ALPHA, DB_PATH, EMBEDDING_MODEL, EMBEDDING_DEVICE,
        API_PORT, DEEP_BUDGET, QUICK_BUDGET, count_tokens,
    )

    assert ALPHA == 0.3
    assert DEEP_BUDGET == 8000
    assert QUICK_BUDGET == 2000
    assert API_PORT == 3101
    assert EMBEDDING_MODEL in ("BAAI/bge-large-en-v1.5", "BAAI/bge-base-en-v1.5")
    assert EMBEDDING_DEVICE in ("cuda", "cpu")
    assert count_tokens("hello world") > 0


def test_setup_steps_template():
    """Test that the template is well-formed."""
    from server.models import SETUP_STEPS_TEMPLATE

    assert len(SETUP_STEPS_TEMPLATE) == 14

    # Check ordering
    orders = [s[2] for s in SETUP_STEPS_TEMPLATE]
    assert orders == list(range(1, 15))

    # Check phases
    phases = [s[0] for s in SETUP_STEPS_TEMPLATE]
    assert phases[0] == "install"
    assert phases[-1] == "ready"

    # Check all have titles
    for phase, step, order, title, desc, prompt in SETUP_STEPS_TEMPLATE:
        assert title, f"Step {step} has no title"
        assert desc, f"Step {step} has no description"
