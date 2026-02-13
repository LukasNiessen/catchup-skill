"""Tests for job registry CRUD operations."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure library modules are discoverable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.jobs import (
    create_job,
    delete_job,
    get_job,
    list_jobs,
    resolve_python_executable,
    update_job_run_status,
)


@pytest.fixture
def jobs_file(tmp_path):
    """Creates a temporary jobs.json file path."""
    return tmp_path / "jobs.json"


class TestCreateJob:
    """Tests for create_job()."""

    def test_creates_job_with_id(self, jobs_file):
        job = create_job(
            topic="AI news",
            schedule="0 6 * * *",
            email="test@example.com",
            args_dict={"quick": True, "days": 7},
            filepath=jobs_file,
        )
        assert job["id"].startswith("cu_")
        assert len(job["id"]) == 9  # cu_ + 6 chars
        assert job["topic"] == "AI news"
        assert job["schedule"] == "0 6 * * *"
        assert job["email"] == "test@example.com"
        assert job["args"]["quick"] is True
        assert job["run_count"] == 0
        assert job["last_run"] is None

    def test_persists_to_disk(self, jobs_file):
        create_job("test", "0 6 * * *", "a@b.com", {}, filepath=jobs_file)
        assert jobs_file.exists()
        data = json.loads(jobs_file.read_text())
        assert len(data) == 1

    def test_multiple_jobs(self, jobs_file):
        create_job("topic1", "0 6 * * *", "a@b.com", {}, filepath=jobs_file)
        create_job("topic2", "0 7 * * *", "c@d.com", {}, filepath=jobs_file)
        data = json.loads(jobs_file.read_text())
        assert len(data) == 2
        assert data[0]["id"] != data[1]["id"]

    def test_captures_python_executable(self, jobs_file):
        job = create_job("test", "0 6 * * *", "a@b.com", {}, filepath=jobs_file)
        assert job["python_executable"] == sys.executable

    def test_custom_python_executable(self, jobs_file):
        job = create_job(
            "test", "0 6 * * *", "a@b.com", {},
            python_executable="/usr/bin/python3",
            filepath=jobs_file,
        )
        assert job["python_executable"] == "/usr/bin/python3"


class TestListJobs:
    """Tests for list_jobs()."""

    def test_empty_registry(self, jobs_file):
        jobs = list_jobs(jobs_file)
        assert jobs == []

    def test_lists_all_jobs(self, jobs_file):
        create_job("topic1", "0 6 * * *", "a@b.com", {}, filepath=jobs_file)
        create_job("topic2", "0 7 * * *", "c@d.com", {}, filepath=jobs_file)
        jobs = list_jobs(jobs_file)
        assert len(jobs) == 2


class TestGetJob:
    """Tests for get_job()."""

    def test_get_existing_job(self, jobs_file):
        created = create_job("test", "0 6 * * *", "a@b.com", {}, filepath=jobs_file)
        found = get_job(created["id"], jobs_file)
        assert found is not None
        assert found["id"] == created["id"]
        assert found["topic"] == "test"

    def test_get_nonexistent_job(self, jobs_file):
        assert get_job("cu_NONEXIST", jobs_file) is None


class TestDeleteJob:
    """Tests for delete_job()."""

    def test_delete_existing_job(self, jobs_file):
        created = create_job("test", "0 6 * * *", "a@b.com", {}, filepath=jobs_file)
        result = delete_job(created["id"], jobs_file)
        assert result is True
        assert get_job(created["id"], jobs_file) is None

    def test_delete_nonexistent_job(self, jobs_file):
        result = delete_job("cu_NONEXIST", jobs_file)
        assert result is False

    def test_delete_preserves_other_jobs(self, jobs_file):
        job1 = create_job("topic1", "0 6 * * *", "a@b.com", {}, filepath=jobs_file)
        job2 = create_job("topic2", "0 7 * * *", "c@d.com", {}, filepath=jobs_file)
        delete_job(job1["id"], jobs_file)
        remaining = list_jobs(jobs_file)
        assert len(remaining) == 1
        assert remaining[0]["id"] == job2["id"]


class TestUpdateJobRunStatus:
    """Tests for update_job_run_status()."""

    def test_update_success(self, jobs_file):
        created = create_job("test", "0 6 * * *", "a@b.com", {}, filepath=jobs_file)
        result = update_job_run_status(created["id"], "success", filepath=jobs_file)
        assert result is True
        updated = get_job(created["id"], jobs_file)
        assert updated["last_status"] == "success"
        assert updated["last_error"] is None
        assert updated["run_count"] == 1
        assert updated["last_run"] is not None

    def test_update_error(self, jobs_file):
        created = create_job("test", "0 6 * * *", "a@b.com", {}, filepath=jobs_file)
        result = update_job_run_status(
            created["id"], "error", error="API timeout", filepath=jobs_file
        )
        assert result is True
        updated = get_job(created["id"], jobs_file)
        assert updated["last_status"] == "error"
        assert updated["last_error"] == "API timeout"

    def test_update_nonexistent_job(self, jobs_file):
        result = update_job_run_status("cu_NONEXIST", "success", filepath=jobs_file)
        assert result is False

    def test_run_count_increments(self, jobs_file):
        created = create_job("test", "0 6 * * *", "a@b.com", {}, filepath=jobs_file)
        update_job_run_status(created["id"], "success", filepath=jobs_file)
        update_job_run_status(created["id"], "success", filepath=jobs_file)
        updated = get_job(created["id"], jobs_file)
        assert updated["run_count"] == 2


class TestResolvePythonExecutable:
    """Tests for resolve_python_executable()."""

    def test_returns_string(self):
        result = resolve_python_executable()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_matches_sys_executable(self):
        assert resolve_python_executable() == sys.executable
