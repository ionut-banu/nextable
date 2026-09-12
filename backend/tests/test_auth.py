"""Staff authentication, spec sections 8.1 and 10."""
from tests.conftest import STAFF_PASSWORD

SESSION_COOKIE = "nextable_session"


def test_login_with_the_staff_password_opens_a_session(client):
    response = client.post("/api/auth/login", json={"password": STAFF_PASSWORD})

    assert response.status_code == 204
    assert SESSION_COOKIE in response.cookies


def test_the_session_cookie_is_httponly_and_samesite_lax(client):
    response = client.post("/api/auth/login", json={"password": STAFF_PASSWORD})

    header = response.headers["set-cookie"].lower()
    assert "httponly" in header
    assert "samesite=lax" in header


def test_the_wrong_password_is_rejected(client):
    response = client.post("/api/auth/login", json={"password": "not-it"})

    assert response.status_code == 401
    assert response.json() == {"detail": "That password is not right."}
    assert SESSION_COOKIE not in response.cookies


def test_me_without_a_session_is_unauthorised(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_a_session_is_fine(host):
    assert host.get("/api/auth/me").status_code == 200


def test_logout_ends_the_session(host):
    assert host.post("/api/auth/logout").status_code == 204
    assert host.get("/api/auth/me").status_code == 401


def test_a_forged_session_cookie_is_refused(client):
    client.cookies.set(SESSION_COOKIE, "host.forged-signature")

    assert client.get("/api/auth/me").status_code == 401


def test_repeated_wrong_passwords_are_rate_limited(client):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"password": "no"}).status_code == 401

    blocked = client.post("/api/auth/login", json={"password": "no"})
    assert blocked.status_code == 429

    # The lockout holds even when the caller finally gets the password right.
    assert client.post("/api/auth/login", json={"password": STAFF_PASSWORD}).status_code == 429
