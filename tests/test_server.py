import pytest

import server


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(server, "ask_claude", lambda prompt: f"<p>{prompt[:20]}</p>")
    return server.app.test_client()


def test_generates_a_section(client):
    res = client.post("/api/section", json={"product": "Bosch Serie 4", "section": "specs"})
    assert res.status_code == 200
    assert res.get_json()["section"] == "specs"
    assert res.get_json()["product"] == "Bosch Serie 4"


@pytest.mark.parametrize("body", [{"product": "", "section": "short"}, {"product": "a", "section": "short"}])
def test_rejects_short_product_names(client, body):
    assert client.post("/api/section", json=body).status_code == 400


def test_rejects_unknown_sections(client):
    assert client.post("/api/section", json={"product": "TV", "section": "all"}).status_code == 400


def test_non_json_body_is_a_400_not_a_crash(client):
    res = client.post("/api/section", data="product=TV", content_type="text/plain")
    assert res.status_code == 400


def test_non_string_fields_are_a_400_not_a_crash(client):
    assert client.post("/api/section", json={"product": 123, "section": None}).status_code == 400


def test_provider_errors_are_not_leaked(client, monkeypatch):
    def fail(prompt):
        raise RuntimeError("secret api detail")

    monkeypatch.setattr(server, "ask_claude", fail)
    res = client.post("/api/section", json={"product": "TV", "section": "short"})
    assert res.status_code == 502
    assert "secret" not in res.get_data(as_text=True)


def test_index_serves_the_search_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"<html" in res.data.lower()
