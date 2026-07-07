import pytest
import jwt
from datetime import datetime, timedelta


class TestJWTAuth:
    def test_get_profile_without_token(self, customer_client):
        resp = customer_client.get('/customers/profile')
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"]["code"] == "MISSING_TOKEN"

    def test_get_profile_with_invalid_token(self, customer_client):
        resp = customer_client.get(
            '/customers/profile',
            headers={"Authorization": "Bearer invalidtoken"}
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"]["code"] == "INVALID_TOKEN"

    def test_get_profile_with_expired_token(self, customer_app, customer_client):
        expired = jwt.encode(
            {"customer_id": "test", "email": "test@test.com", "exp": datetime.utcnow() - timedelta(hours=1)},
            customer_app.config.get('JWT_SECRET', 'test-secret'),
            algorithm="HS256"
        )
        resp = customer_client.get(
            '/customers/profile',
            headers={"Authorization": f"Bearer {expired}"}
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"]["code"] == "TOKEN_EXPIRED"

    def test_get_profile_with_valid_token(self, customer_client, auth_headers):
        resp = customer_client.get('/customers/profile', headers=auth_headers)
        assert resp.status_code == 200

    def test_missing_bearer_prefix(self, customer_client):
        resp = customer_client.get(
            '/customers/profile',
            headers={"Authorization": "sometoken"}
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"]["code"] == "MISSING_TOKEN"
