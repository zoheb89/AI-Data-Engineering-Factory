import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from cinvent import db
from cinvent.workflow import run_stage, gate_check


def setup_project():
    db.init_db()
    return db.create_project("Demo", "Hospital HMS", "Modernize hospital HMS", "Healthcare", "Databricks")


def seed(pid, stages):
    for stage in stages:
        db.add_artifact(pid, stage, f"{stage}.json", "json", "{}")


def test_environment_assessment_requires_discovery():
    pid = setup_project()
    db.add_artifact(pid, "intake", "intake_pack.json", "json", "{}")
    result = run_stage(pid, "environment_assessment")
    assert "discovery" in result["error"]


def test_architecture_requires_environment_assessment():
    pid = setup_project()
    seed(pid, ["intake", "discovery"])
    result = run_stage(pid, "architecture")
    assert "environment_assessment" in result["error"]


def test_engineering_requires_architecture_approval():
    pid = setup_project()
    seed(pid, ["intake", "discovery", "environment_assessment", "assessment", "architecture", "metadata"])
    result = run_stage(pid, "engineering")
    assert "architecture_approval" in result["error"]
