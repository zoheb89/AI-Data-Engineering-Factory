from c_invent.services.project_store import ProjectStore


def test_legacy_empty_projects_are_consolidated(tmp_path):
    db = ProjectStore(tmp_path / "cinvent.db")
    old1 = db.create_project("Untitled Customer Project", "Unknown", "", source="legacy")
    old2 = db.create_project("Untitled Customer Project", "Unknown", "", source="legacy")
    keep = db.ensure_single_clean_workspace()
    ids = [p["id"] for p in db.list_projects()]
    assert keep in ids
    assert len(ids) == 1
    assert db.get_project(keep)["source"] == "system"


def test_explicit_blank_project_is_not_deleted(tmp_path):
    db = ProjectStore(tmp_path / "cinvent.db")
    system = db.create_project("Untitled Customer Project", "Unknown", "", source="system")
    user = db.create_project("Untitled Customer Project", "Unknown", "", source="user")
    db.ensure_single_clean_workspace()
    ids = {p["id"] for p in db.list_projects()}
    assert system in ids
    assert user in ids
