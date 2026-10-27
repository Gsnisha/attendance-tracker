import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_fd, _path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE"] = _path

import app as app_module  # noqa: E402


@pytest.fixture()
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json()["status"] == "ok"


def test_all_pages_load(client):
    for path in ("/", "/students", "/mark", "/report"):
        assert client.get(path).status_code == 200


def test_add_mark_and_report(client):
    client.post("/students", data={"roll_no": "R1", "name": "Asha", "course": "CS"})
    assert b"Asha" in client.get("/students").data
    client.post("/mark", data={"day": "2026-01-05", "sid": "1", "status_1": "Absent"})
    page = client.get("/report").data
    assert b"Asha" in page and b"0%" in page
