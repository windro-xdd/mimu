import unittest

from fastapi.testclient import TestClient

from backend.services.auth import (
    app,
    reset_auth_state,
    session_manager,
    user_repository,
)
from backend.services.auth.security import (
    decode_refresh_token,
    hash_password,
    verify_password,
)


class AuthServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        reset_auth_state()
        self.client = TestClient(app, base_url="https://testserver.local")

    def register_user(self, username: str, email: str, password: str) -> None:
        payload = {"username": username, "email": email, "password": password}
        response = self.client.post("/auth/register", json=payload)
        self.assertEqual(response.status_code, 201, msg=response.text)

    def create_user_direct(self, username: str, email: str, password: str, *, role: str = "user") -> User:
        password_hash = hash_password(password)
        return user_repository.create_user(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
        )

    def login(self, identifier: str, password: str) -> None:
        payload = {"identifier": identifier, "password": password}
        response = self.client.post("/auth/login", json=payload)
        self.assertEqual(response.status_code, 200, msg=response.text)

    def test_register_creates_user_with_secure_cookies(self) -> None:
        payload = {"username": "alice", "email": "alice@example.com", "password": "Secret123!"}
        response = self.client.post("/auth/register", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("user", data)
        stored_user = user_repository.get_by_username("alice")
        self.assertIsNotNone(stored_user)
        assert stored_user is not None
        self.assertNotEqual(stored_user.password_hash, payload["password"])
        self.assertTrue(verify_password(payload["password"], stored_user.password_hash))

        cookie_headers = response.headers.get_list("set-cookie")
        access_cookie = next(header for header in cookie_headers if header.startswith("access_token="))
        refresh_cookie = next(header for header in cookie_headers if header.startswith("refresh_token="))
        csrf_cookie = next(header for header in cookie_headers if header.startswith("csrf_token="))

        self.assertIn("HttpOnly", access_cookie)
        self.assertIn("Secure", access_cookie)
        self.assertIn("HttpOnly", refresh_cookie)
        self.assertIn("Secure", refresh_cookie)
        self.assertNotIn("HttpOnly", csrf_cookie)
        self.assertIn("Secure", csrf_cookie)

    def test_register_rejects_duplicate_username_and_email(self) -> None:
        self.register_user("robin", "robin@example.com", "Password123!")

        response_username_conflict = self.client.post(
            "/auth/register",
            json={"username": "robin", "email": "different@example.com", "password": "Password123!"},
        )
        self.assertEqual(response_username_conflict.status_code, 400)

        response_email_conflict = self.client.post(
            "/auth/register",
            json={"username": "different", "email": "robin@example.com", "password": "Password123!"},
        )
        self.assertEqual(response_email_conflict.status_code, 400)

    def test_login_with_valid_credentials_sets_cookies(self) -> None:
        self.create_user_direct("maria", "maria@example.com", "SuperPass123!")
        response = self.client.post(
            "/auth/login",
            json={"identifier": "maria", "password": "SuperPass123!"},
        )
        self.assertEqual(response.status_code, 200)
        cookie_headers = response.headers.get_list("set-cookie")
        self.assertTrue(any(header.startswith("access_token=") for header in cookie_headers))
        self.assertTrue(any(header.startswith("refresh_token=") for header in cookie_headers))
        self.assertTrue(any(header.startswith("csrf_token=") for header in cookie_headers))

    def test_login_rejects_invalid_credentials(self) -> None:
        self.create_user_direct("jamie", "jamie@example.com", "AnotherPass123!")
        response = self.client.post(
            "/auth/login",
            json={"identifier": "jamie", "password": "WrongPassword!"},
        )
        self.assertEqual(response.status_code, 401)

    def test_logout_requires_csrf(self) -> None:
        self.create_user_direct("lewis", "lewis@example.com", "Password123!")
        self.login("lewis", "Password123!")
        response = self.client.post("/auth/logout")
        self.assertEqual(response.status_code, 403)

    def test_logout_clears_cookies_and_revokes_refresh_token(self) -> None:
        self.create_user_direct("nina", "nina@example.com", "Password123!")
        self.login("nina", "Password123!")

        refresh_token = self.client.cookies.get("refresh_token")
        csrf_token = self.client.cookies.get("csrf_token")
        self.assertIsNotNone(refresh_token)
        assert refresh_token is not None
        payload = decode_refresh_token(refresh_token, verify_exp=False)
        original_jti = payload["jti"]
        self.assertTrue(session_manager.refresh_tokens.is_active(original_jti))

        response = self.client.post("/auth/logout", headers={"X-CSRF-Token": csrf_token})
        self.assertEqual(response.status_code, 200)
        cookie_headers = response.headers.get_list("set-cookie")
        for cookie_name in ("access_token", "refresh_token", "csrf_token"):
            header = next((h for h in cookie_headers if h.startswith(f"{cookie_name}=")), None)
            self.assertIsNotNone(header)
            assert header is not None
            self.assertIn("Max-Age=0", header)

        self.assertFalse(session_manager.refresh_tokens.is_active(original_jti))

    def test_protected_route_requires_authentication(self) -> None:
        response = self.client.get("/auth/me")
        self.assertEqual(response.status_code, 401)

    def test_protected_route_requires_admin_role(self) -> None:
        self.create_user_direct("oliver", "oliver@example.com", "Password123!")
        self.login("oliver", "Password123!")
        response = self.client.get("/auth/admin")
        self.assertEqual(response.status_code, 403)

    def test_admin_route_succeeds_for_admin_user(self) -> None:
        self.create_user_direct("sara", "sara@example.com", "Password123!", role="admin")
        self.login("sara", "Password123!")
        response = self.client.get("/auth/admin")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user"]["role"], "admin")

    def test_refresh_rotates_refresh_token(self) -> None:
        self.create_user_direct("taylor", "taylor@example.com", "Password123!")
        self.login("taylor", "Password123!")

        original_refresh = self.client.cookies.get("refresh_token")
        csrf_token = self.client.cookies.get("csrf_token")
        self.assertIsNotNone(original_refresh)
        assert original_refresh is not None
        payload = decode_refresh_token(original_refresh, verify_exp=True)
        original_jti = payload["jti"]
        self.assertTrue(session_manager.refresh_tokens.is_active(original_jti))

        response = self.client.post("/auth/refresh", headers={"X-CSRF-Token": csrf_token})
        self.assertEqual(response.status_code, 200)
        new_refresh = self.client.cookies.get("refresh_token")
        self.assertIsNotNone(new_refresh)
        self.assertNotEqual(original_refresh, new_refresh)

        rotated_payload = decode_refresh_token(new_refresh, verify_exp=True)
        self.assertNotEqual(rotated_payload["jti"], original_jti)
        self.assertFalse(session_manager.refresh_tokens.is_active(original_jti))
        self.assertTrue(session_manager.refresh_tokens.is_active(rotated_payload["jti"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
