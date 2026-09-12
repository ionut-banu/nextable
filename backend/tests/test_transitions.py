"""The status lifecycle, spec 5.2. Enforced in the service, surfaced as 409."""
import pytest


def add(host, name="Party", size=2):
    return host.post("/api/parties", json={"name": name, "size": size}).json()


def act(host, party, action):
    return host.post(f"/api/parties/{party['id']}/{action}")


# --- the legal path --------------------------------------------------------


def test_notify_moves_a_waiting_party_and_stamps_the_time(host):
    party = add(host)

    notified = act(host, party, "notify").json()

    assert notified["status"] == "NOTIFIED"
    assert notified["notified_at"] is not None
    assert notified["seated_at"] is None
    assert notified["closed_at"] is None


def test_seating_a_notified_party_closes_it(host):
    party = add(host)
    act(host, party, "notify")

    seated = act(host, party, "seat").json()

    assert seated["status"] == "SEATED"
    assert seated["seated_at"] is not None
    assert seated["closed_at"] is not None


def test_a_party_can_be_seated_straight_from_the_queue(host):
    party = add(host)

    seated = act(host, party, "seat").json()

    assert seated["status"] == "SEATED"
    assert seated["notified_at"] is None
    assert seated["seated_at"] is not None


def test_a_called_party_that_never_arrives_is_a_no_show(host):
    party = add(host)
    act(host, party, "notify")

    assert act(host, party, "no-show").json()["status"] == "NO_SHOW"


@pytest.mark.parametrize("before", [[], ["notify"]])
def test_a_party_can_cancel_before_and_after_being_called(host, before):
    party = add(host)
    for action in before:
        act(host, party, action)

    assert act(host, party, "cancel").json()["status"] == "CANCELLED"


def test_a_timestamp_is_stamped_once_and_not_again(host):
    party = add(host)
    first = act(host, party, "notify").json()

    act(host, party, "seat")
    after_seating = host.get(f"/api/parties/{party['id']}").json()

    assert after_seating["notified_at"] == first["notified_at"]


# --- the illegal ones ------------------------------------------------------


def test_a_party_that_was_never_called_cannot_be_a_no_show(host):
    party = add(host)

    refused = act(host, party, "no-show")

    assert refused.status_code == 409
    assert refused.json() == {"detail": "A party that is WAITING cannot become NO_SHOW."}


def test_a_called_party_cannot_be_called_again(host):
    party = add(host)
    act(host, party, "notify")

    refused = act(host, party, "notify")

    assert refused.status_code == 409
    assert refused.json() == {"detail": "A party that is NOTIFIED cannot become NOTIFIED."}


@pytest.mark.parametrize("closing", ["seat", "cancel"])
@pytest.mark.parametrize("attempt", ["notify", "seat", "no-show", "cancel"])
def test_nothing_moves_a_party_out_of_a_terminal_status(host, closing, attempt):
    party = add(host)
    act(host, party, closing)
    settled = host.get(f"/api/parties/{party['id']}").json()

    refused = act(host, party, attempt)

    assert refused.status_code == 409
    # Refused, not silently ignored: the record is untouched.
    assert host.get(f"/api/parties/{party['id']}").json() == settled


def test_an_illegal_transition_names_both_statuses(host):
    party = add(host)
    act(host, party, "seat")

    detail = act(host, party, "notify").json()["detail"]

    assert "SEATED" in detail
    assert "NOTIFIED" in detail


def test_acting_on_an_unknown_party_is_a_404(host):
    response = host.post("/api/parties/4041/notify")

    assert response.status_code == 404
    assert response.json() == {"detail": "That party is not on the list."}


@pytest.mark.parametrize("action", ["notify", "seat", "no-show", "cancel"])
def test_transitions_refuse_a_caller_without_a_session(client, action):
    assert client.post(f"/api/parties/1/{action}").status_code == 401
