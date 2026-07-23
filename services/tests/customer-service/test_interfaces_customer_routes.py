class TestCustomerAuthRoutes:
    def test_register_customer(self, customer_client):
        resp = customer_client.post('/customers/register', json={
            "name": "Alice",
            "email": "alice@example.com",
            "password": "secure123"
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["customer"]["name"] == "Alice"
        assert data["customer"]["email"] == "alice@example.com"
        assert "token" in data
        assert "id" in data["customer"]

    def test_register_duplicate_email(self, customer_client):
        customer_client.post('/customers/register', json={
            "name": "Alice",
            "email": "dup@example.com",
            "password": "secure123"
        })
        resp = customer_client.post('/customers/register', json={
            "name": "Alice 2",
            "email": "dup@example.com",
            "password": "secure123"
        })
        assert resp.status_code == 409

    def test_register_missing_body(self, customer_client):
        resp = customer_client.post('/customers/register', json={})
        assert resp.status_code == 400

    def test_login_success(self, customer_client):
        customer_client.post('/customers/register', json={
            "name": "Login Test",
            "email": "login@example.com",
            "password": "secure123"
        })
        resp = customer_client.post('/customers/login', json={
            "email": "login@example.com",
            "password": "secure123"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["customer"]["email"] == "login@example.com"
        assert "token" in data

    def test_login_wrong_password(self, customer_client):
        customer_client.post('/customers/register', json={
            "name": "Wrong",
            "email": "wrong@example.com",
            "password": "secure123"
        })
        resp = customer_client.post('/customers/login', json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert resp.status_code == 401


class TestCustomerProfileRoutes:
    def test_get_profile(self, customer_client, auth_headers):
        resp = customer_client.get('/customers/profile', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["email"] == "test@example.com"

    def test_update_profile(self, customer_client, auth_headers):
        resp = customer_client.put('/customers/profile', json={"name": "New Name"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "New Name"

    def test_update_profile_missing_body(self, customer_client, auth_headers):
        resp = customer_client.put('/customers/profile', json={}, headers=auth_headers)
        assert resp.status_code == 400


class TestCustomerAddressRoutes:
    def test_get_addresses(self, customer_client, auth_headers):
        resp = customer_client.get('/customers/addresses', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["addresses"] == []

    def test_add_address(self, customer_client, auth_headers):
        resp = customer_client.post('/customers/addresses', json={
            "label": "Home",
            "street": "1 Rue de Paris",
            "city": "Paris",
            "postal_code": "75001"
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["label"] == "Home"
        assert data["street"] == "1 Rue de Paris"

    def test_update_address(self, customer_client, auth_headers):
        create_resp = customer_client.post('/customers/addresses', json={
            "label": "Old", "street": "Old St", "city": "Paris"
        }, headers=auth_headers)
        addr_id = create_resp.get_json()["id"]
        resp = customer_client.put(
            f'/customers/addresses/{addr_id}',
            json={"label": "New", "city": "Lyon"},
            headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.get_json()["label"] == "New"
        assert resp.get_json()["city"] == "Lyon"

    def test_delete_address(self, customer_client, auth_headers):
        create_resp = customer_client.post('/customers/addresses', json={
            "label": "Temp", "street": "T", "city": "X"
        }, headers=auth_headers)
        addr_id = create_resp.get_json()["id"]
        resp = customer_client.delete(f'/customers/addresses/{addr_id}', headers=auth_headers)
        assert resp.status_code == 204


class TestCustomerOrderRoutes:
    def test_get_orders(self, customer_client, auth_headers):
        resp = customer_client.get('/customers/orders', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["orders"] == []


class TestErrorBranches:
    def test_login_missing_body(self, customer_client):
        resp = customer_client.post('/customers/login', json={})
        assert resp.status_code == 400

    def test_add_address_missing_body(self, customer_client, auth_headers):
        resp = customer_client.post('/customers/addresses', json={}, headers=auth_headers)
        assert resp.status_code == 400

    def test_update_address_missing_body(self, customer_client, auth_headers):
        resp = customer_client.put('/customers/addresses/addr-1', json={}, headers=auth_headers)
        assert resp.status_code == 400

    def test_update_unknown_address_returns_404(self, customer_client, auth_headers):
        resp = customer_client.put(
            '/customers/addresses/unknown', json={"label": "Maison"}, headers=auth_headers
        )
        assert resp.status_code == 404

    def test_delete_unknown_address_returns_404(self, customer_client, auth_headers):
        resp = customer_client.delete('/customers/addresses/unknown', headers=auth_headers)
        assert resp.status_code == 404
