"""Operational settings, spec 7 and 8.2."""


def test_the_defaults_are_the_cold_start_numbers_from_the_spec(host):
    config = host.get("/api/config").json()

    assert config["restaurant_name"] == "The Blue Fig"
    assert config["history_window"] == 20
    assert config["smoothing_constant"] == 5
    assert config["buckets"]["SMALL"] == {"default_turn_minutes": 25, "table_count": 8}
    assert config["buckets"]["MEDIUM"] == {"default_turn_minutes": 40, "table_count": 6}
    assert config["buckets"]["LARGE"] == {"default_turn_minutes": 55, "table_count": 3}
    assert config["buckets"]["XLARGE"] == {"default_turn_minutes": 75, "table_count": 1}


def test_settings_can_be_changed_and_stay_changed(host):
    config = host.get("/api/config").json()
    config["restaurant_name"] = "Pino's"
    config["buckets"]["SMALL"]["default_turn_minutes"] = 35

    saved = host.put("/api/config", json=config).json()

    assert saved["restaurant_name"] == "Pino's"
    assert host.get("/api/config").json()["buckets"]["SMALL"]["default_turn_minutes"] == 35


def test_changing_the_table_count_changes_the_next_quote(host):
    config = host.get("/api/config").json()
    config["buckets"]["SMALL"]["table_count"] = 1
    host.put("/api/config", json=config)

    host.post("/api/parties", json={"name": "First", "size": 2})
    second = host.post("/api/parties", json={"name": "Second", "size": 2}).json()

    # One two-top table in play, so the second couple waits a full turn.
    assert second["quoted_wait_minutes"] == 25


def test_the_guest_page_shows_the_new_restaurant_name(client, host):
    party = host.post("/api/parties", json={"name": "Dana", "size": 2}).json()
    config = host.get("/api/config").json()
    config["restaurant_name"] = "Pino's"
    host.put("/api/config", json=config)

    body = client.get(f"/api/waitlist/{party['token']}").json()

    assert body["restaurant_name"] == "Pino's"


def test_nonsense_settings_are_rejected(host):
    config = host.get("/api/config").json()
    config["buckets"]["SMALL"]["table_count"] = 0

    assert host.put("/api/config", json=config).status_code == 422


def test_config_refuses_a_caller_without_a_session(client):
    assert client.get("/api/config").status_code == 401
    assert client.put("/api/config", json={}).status_code == 401
