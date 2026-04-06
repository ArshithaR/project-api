from app import db
from app.models import Alert, API, PasswordResetCode, User


def test_app_creation(app):
    """Test that app is created."""
    assert app is not None
    assert app.config["TESTING"] is True


def test_home_page(client):
    """Test home page redirects to login."""
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")


def test_login_page(client):
    """Test login page loads."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Login" in response.data or b"login" in response.data


def test_register_page(client):
    """Test register page loads."""
    response = client.get("/auth/register")
    assert response.status_code == 200
    assert b"Register" in response.data or b"register" in response.data


def test_register_user(app, client):
    """Test user registration."""
    with app.app_context():
        client.post("/auth/register", data={
            "username": "testuser",
            "email": "test@test.com",
            "password": "password123"
        }, follow_redirects=True)

        user = User.query.filter_by(username="testuser").first()
        assert user is not None
        assert user.email == "test@test.com"


def test_forgot_password_page_loads(client):
    """Test forgot password page loads."""
    response = client.get("/auth/forgot-password")
    assert response.status_code == 200
    assert b"Forgot Password" in response.data


def test_password_reset_flow(app, client):
    """User can request reset code and change password."""
    with app.app_context():
        user = User(username="resetuser", email="reset@test.com")
        user.set_password("oldpass123")
        db.session.add(user)
        db.session.commit()

    app.config["MAIL_SUPPRESS_SEND"] = True

    response = client.post("/auth/forgot-password", data={
        "email": "reset@test.com"
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="reset@test.com").first()
        reset_code = PasswordResetCode.query.filter_by(user_id=user.id, used=False).order_by(PasswordResetCode.created_at.desc()).first()
        assert reset_code is not None
        code = reset_code.code

    reset_response = client.post("/auth/reset-password", data={
        "email": "reset@test.com",
        "code": code,
        "password": "newpass123",
        "confirm_password": "newpass123"
    }, follow_redirects=True)
    assert reset_response.status_code == 200

    login_response = client.post("/auth/login", data={
        "username": "resetuser",
        "password": "newpass123"
    }, follow_redirects=True)
    assert login_response.status_code == 200


def test_login_user(app, client):
    """Test user login."""
    with app.app_context():
        user = User(username="testuser", email="test@test.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

    response = client.post("/auth/login", data={
        "username": "testuser",
        "password": "password123"
    }, follow_redirects=True)

    assert response.status_code == 200


def test_dashboard_requires_login(client):
    """Test dashboard requires login."""
    response = client.get("/dashboard")
    assert response.status_code == 302


def test_metrics_endpoint_exposes_prometheus_text(client):
    """Test Prometheus metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"api_monitor_http_requests_total" in response.data


def test_devops_page_loads_after_login(app, client):
    """Test devops page after login."""
    with app.app_context():
        user = User(username="devops", email="devops@test.com")
        user.set_password("secret123")
        db.session.add(user)
        db.session.commit()

    response = client.post("/auth/login", data={
        "username": "devops",
        "password": "secret123"
    }, follow_redirects=True)

    assert response.status_code == 200

    devops_response = client.get("/devops")
    assert devops_response.status_code == 200


def test_alert_count_endpoint_returns_active_alert_total(app, client):
    """Navbar alert badge should reflect active alerts."""
    with app.app_context():
        user = User(username="alertuser", email="alert@test.com")
        user.set_password("secret123")
        db.session.add(user)
        db.session.commit()

        api = API(name="Alert API", url="https://example.com", user_id=user.id)
        db.session.add(api)
        db.session.commit()

        db.session.add(Alert(
            api_id=api.id,
            alert_type="offline",
            severity="critical",
            message="API is offline",
            is_active=True,
        ))
        db.session.add(Alert(
            api_id=api.id,
            alert_type="slow",
            severity="warning",
            message="API is slow",
            is_active=True,
        ))
        db.session.commit()

    login_response = client.post("/auth/login", data={
        "username": "alertuser",
        "password": "secret123"
    }, follow_redirects=True)
    assert login_response.status_code == 200

    response = client.get("/api/alerts/count")
    assert response.status_code == 200
    assert response.get_json()["count"] == 2


def test_delete_api_removes_related_alerts(app, client):
    """Deleting an API should also delete its alerts."""
    with app.app_context():
        user = User(username="owner", email="owner@test.com")
        user.set_password("secret123")
        db.session.add(user)
        db.session.commit()

        api = API(name="Demo API", url="https://example.com", user_id=user.id)
        db.session.add(api)
        db.session.commit()

        alert = Alert(
            api_id=api.id,
            alert_type="offline",
            severity="critical",
            message="API is offline",
            is_active=True,
        )
        db.session.add(alert)
        db.session.commit()
        api_id = api.id
        alert_id = alert.id

    login_response = client.post("/auth/login", data={
        "username": "owner",
        "password": "secret123"
    }, follow_redirects=True)
    assert login_response.status_code == 200

    delete_response = client.post(f"/api/delete/{api_id}", follow_redirects=True)
    assert delete_response.status_code == 200

    with app.app_context():
        assert API.query.get(api_id) is None
        assert Alert.query.get(alert_id) is None
