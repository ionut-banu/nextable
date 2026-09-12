"""Adding and reading parties, spec 8.2."""
import pytest


def add(host, name="Whitcomb", size=2, **extra):
    response = host.post("/api/parties", json={"name": name, "size": size, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_adding_a_party_returns_it_in_full(host):
    party = add(host, name="Dana Whitcomb", size=4, phone="555 0147", note="Highchair")

    assert party["name"] == "Dana Whitcomb"
    assert party["size"] == 4
    assert party["phone"] == "555 0147"
    assert party["note"] == "Highchair"
    assert party["status"] == "WAITING"
    assert party["bucket"] == "MEDIUM"
    assert party["notified_at"] is None
    assert party["seated_at"] is None
    assert party["closed_at"] is None


def test_the_host_gets_the_token_so_it_can_render_the_guest_link(host):
    party = add(host)

    assert len(party["token"]) >= 20


def test_two_parties_never_share_a_token(host):
    assert add(host, name="One")["token"] != add(host, name="Two")["token"]


def test_the_first_party_of_the_night_is_quoted_nothing(host):
    party = add(host, size=2)

    assert party["quoted_wait_minutes"] == 0
    assert party["position_in_line"] == 1
    assert party["current_estimate_minutes"] == 0


def test_the_quote_appears_once_the_bucket_fills_up(host):
    # Eight two-tops in play, so the ninth small party waits one turn.
    for index in range(8):
        add(host, name=f"Small {index}", size=2)

    ninth = add(host, name="Ninth", size=2)

    assert ninth["position_in_line"] == 9
    assert ninth["quoted_wait_minutes"] == 25


def test_position_counts_only_the_party_s_own_size_bucket(host):
    for index in range(3):
        add(host, name=f"Four-top {index}", size=4)

    two_top = add(host, name="Couple", size=2)

    # Three parties are physically ahead, but none of them want a two-top.
    assert two_top["position_in_line"] == 1
    assert two_top["current_estimate_minutes"] == 0


def test_the_quote_is_frozen_but_the_estimate_is_live(host):
    first = add(host, name="First", size=8)
    add(host, name="Second", size=8)

    reread = host.get(f"/api/parties/{first['id']}").json()

    assert reread["quoted_wait_minutes"] == first["quoted_wait_minutes"] == 0
    assert reread["current_estimate_minutes"] == 0
    assert reread["position_in_line"] == 1


def test_a_party_behind_sees_its_estimate_fall_as_the_queue_clears(host):
    ahead = add(host, name="Ahead", size=8)
    behind = add(host, name="Behind", size=8)

    assert host.get(f"/api/parties/{behind['id']}").json()["current_estimate_minutes"] == 75

    host.post(f"/api/parties/{ahead['id']}/seat")

    assert host.get(f"/api/parties/{behind['id']}").json()["current_estimate_minutes"] == 0


@pytest.mark.parametrize("body", [
    {"name": "", "size": 2},
    {"name": "   ", "size": 2},
    {"size": 2},
    {"name": "Nobody", "size": 0},
    {"name": "Nobody", "size": -3},
    {"name": "Nobody"},
])
def test_a_bad_body_is_rejected_before_anything_is_written(host, body):
    assert host.post("/api/parties", json=body).status_code == 422
    assert host.get("/api/parties").json() == []


def test_the_queue_lists_active_parties_oldest_first(host):
    add(host, name="First")
    add(host, name="Second")
    add(host, name="Third")

    queue = host.get("/api/parties").json()

    assert [party["name"] for party in queue] == ["First", "Second", "Third"]


def test_the_queue_leaves_out_parties_that_have_gone(host):
    staying = add(host, name="Staying")
    leaving = add(host, name="Leaving")
    host.post(f"/api/parties/{leaving['id']}/cancel")

    queue = host.get("/api/parties").json()

    assert [party["id"] for party in queue] == [staying["id"]]


def test_asking_for_all_parties_includes_the_ones_that_have_gone(host):
    add(host, name="Staying")
    leaving = add(host, name="Leaving")
    host.post(f"/api/parties/{leaving['id']}/cancel")

    everyone = host.get("/api/parties", params={"status": "all"}).json()

    assert {party["name"] for party in everyone} == {"Staying", "Leaving"}


def test_a_closed_party_has_no_position_or_estimate(host):
    party = add(host)
    host.post(f"/api/parties/{party['id']}/seat")

    seated = host.get(f"/api/parties/{party['id']}").json()

    assert seated["position_in_line"] is None
    assert seated["current_estimate_minutes"] is None


def test_an_unknown_party_is_not_found(host):
    response = host.get("/api/parties/4041")

    assert response.status_code == 404
    # Asserting our own wording, so a missing route cannot satisfy this test.
    assert response.json() == {"detail": "That party is not on the list."}


@pytest.mark.parametrize("method,path", [
    ("post", "/api/parties"),
    ("get", "/api/parties"),
    ("get", "/api/parties/1"),
])
def test_host_routes_refuse_a_caller_without_a_session(client, method, path):
    assert getattr(client, method)(path).status_code == 401
