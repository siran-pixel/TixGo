from models import User


def test_signup_direct_success(client, app):
    """Test user signup directly creates active account and logs in."""
    response = client.post(
        "/signup",
        json={
            "full_name": "Alice Wonderland",
            "email": "alice@example.com",
            "password": "SecurePassword123",
            "confirm_password": "SecurePassword123",
            "phone": "9876543222",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True

    with app.app_context():
        user = User.query.filter_by(email="alice@example.com").first()
        assert user is not None
        assert user.is_verified is True


def test_signup_duplicate_email(client):
    """Test signing up with an existing email returns error."""
    response = client.post(
        "/signup",
        json={
            "full_name": "Duplicate User",
            "email": "john@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
            "phone": "9876543210",
        },
    )
    assert response.status_code == 409
    data = response.get_json()
    assert data["success"] is False
    assert "already exists" in data["message"]


def test_login_success(client):
    """Test direct login with correct credentials."""
    response = client.post(
        "/login",
        json={
            "email": "john@example.com",
            "password": "Password123",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True


def test_login_invalid_password(client):
    """Test login fails with incorrect password."""
    response = client.post(
        "/login",
        json={
            "email": "john@example.com",
            "password": "WrongPassword999",
        },
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data["success"] is False


def test_forgot_and_reset_password_flow(client, app):
    """Test forgot password request and direct reset."""
    # 1. Request reset for john
    forgot_res = client.post(
        "/forgot-password",
        json={"email": "john@example.com"},
    )
    assert forgot_res.status_code == 200

    # 2. Reset password
    reset_res = client.post(
        "/reset-password?email=john@example.com",
        json={
            "password": "BrandNewPassword123",
            "confirm_password": "BrandNewPassword123",
        },
    )
    assert reset_res.status_code == 200

    # 3. Verify user can log in with new password
    login_res = client.post(
        "/login",
        json={
            "email": "john@example.com",
            "password": "BrandNewPassword123",
        },
    )
    assert login_res.status_code == 200
    assert login_res.get_json()["success"] is True


def test_signup_invalid_phone_digits(client):
    """Test signing up with less than 10 or more than 10 digits fails."""
    # Less than 10 digits (9 digits)
    res_short = client.post(
        "/signup",
        json={
            "full_name": "Short Phone",
            "email": "shortphone@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
            "phone": "987654321",
        },
    )
    assert res_short.status_code == 400
    assert "10-digit phone number" in res_short.get_json()["message"]

    # More than 10 digits (11 digits)
    res_long = client.post(
        "/signup",
        json={
            "full_name": "Long Phone",
            "email": "longphone@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
            "phone": "98765432101",
        },
    )
    assert res_long.status_code == 400
    assert "10-digit phone number" in res_long.get_json()["message"]

