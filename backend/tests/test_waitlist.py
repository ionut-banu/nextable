"""The guest's own status, spec 8.3. Public, and deliberately minimal."""

GUEST_FIELDS = {
    "restaurant_name",
    "party_first_name",
    "size",
    "status",
    "position_in_line",
    "estimated_wait_minutes",
    "joined_at",
}


def add(host, name="Dana Whitcomb", size=4, **extra):
    return host.post("/api/parties", json={"name": name, "size": size, **extra}).json()


def test_a_guest_needs_no_session(client, host):
    party = add(host)
    client.cookies.clear()

    assert client.get(f"/api/waitlist/{party['token']}").status_code == 200


def test_the_response_carries_exactly_the_promised_fields(client, host):
    party = add(host, phone="555 0147", note="Highchair")

    body = client.get(f"/api/waitlist/{party['token']}").json()

    assert set(body) == GUEST_FIELDS


def test_the_response_leaks_nothing_about_the_party_or_the_queue(client, host):
    party = add(host, name="Dana Whitcomb", phone="555 0147", note="Highchair")

    response = client.get(f"/api/waitlist/{party['token']}")
    raw = response.text

    assert response.status_code == 200
    assert "555 0147" not in raw
    assert "Highchair" not in raw
    assert party["token"] not in raw
    assert "Whitcomb" not in raw


def test_a_guest_is_greeted_by_first_name_only(client, host):
    party = add(host, name="Dana Whitcomb")

    body = client.get(f"/api/waitlist/{party['token']}").json()

    assert body["party_first_name"] == "Dana"


def test_the_guest_sees_the_restaurant_name_and_their_own_size(client, host):
    party = add(host, size=4)

    body = client.get(f"/api/waitlist/{party['token']}").json()

    assert body["restaurant_name"] == "The Blue Fig"
    assert body["size"] == 4


def test_position_is_the_rank_within_the_party_s_own_bucket(client, host):
    for index in range(5):
        add(host, name=f"Four-top {index}", size=4)
    couple = add(host, name="Couple", size=2)

    body = client.get(f"/api/waitlist/{couple['token']}").json()

    # Five parties wait in the room, but none of them want a two-top.
    assert body["position_in_line"] == 1


def test_the_estimate_is_recalculated_not_the_frozen_quote(client, host):
    ahead = add(host, name="Ahead", size=8)
    behind = add(host, name="Behind", size=8)

    before = client.get(f"/api/waitlist/{behind['token']}").json()
    host.post(f"/api/parties/{ahead['id']}/seat")
    after = client.get(f"/api/waitlist/{behind['token']}").json()

    assert before["position_in_line"] == 2
    assert before["estimated_wait_minutes"] == 75
    assert after["position_in_line"] == 1
    assert after["estimated_wait_minutes"] == 0


def test_the_guest_sees_being_called(client, host):
    party = add(host)
    host.post(f"/api/parties/{party['id']}/notify")

    assert client.get(f"/api/waitlist/{party['token']}").json()["status"] == "NOTIFIED"


def test_a_closed_party_has_nothing_left_to_count(client, host):
    party = add(host)
    host.post(f"/api/parties/{party['id']}/seat")

    body = client.get(f"/api/waitlist/{party['token']}").json()

    assert body["status"] == "SEATED"
    assert body["position_in_line"] == 0
    assert body["estimated_wait_minutes"] == 0


def test_an_unknown_token_is_a_plain_404(client):
    response = client.get("/api/waitlist/PPdTDBuEZ1B_r2oTKGiaWg")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}


def test_a_malformed_token_looks_exactly_like_an_unknown_one(client):
    unknown = client.get("/api/waitlist/PPdTDBuEZ1B_r2oTKGiaWg")
    malformed = client.get("/api/waitlist/not-a-real-token")

    assert malformed.status_code == unknown.status_code == 404
    # Our own generic wording, so a missing route cannot satisfy this test.
    assert malformed.json() == unknown.json() == {"detail": "Not found"}
