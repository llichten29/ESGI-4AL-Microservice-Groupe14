import pytest


@pytest.fixture
def app(mock_client):
    from flask import Flask
    from infrastructure.repositories import InMemoryDeliveryRepository
    from application.delivery_service import DeliveryService
    from interfaces.http.routes import routes

    app = Flask(__name__)
    app.config["TESTING"] = True
    repo = InMemoryDeliveryRepository()
    svc = DeliveryService(repository=repo, deliverer_client=mock_client, broker=None)
    app.delivery_service = svc
    app.register_blueprint(routes)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def existing_delivery(client):
    resp = client.post("/deliveries", json={"order_id": "order-1"})
    return resp.get_json()


class TestAssignRoute:
    def test_post_deliveries_returns_201(self, client):
        resp = client.post("/deliveries", json={"order_id": "order-1", "customer_id": "cust-1"})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["order_id"] == "order-1"
        assert data["status"] == "ASSIGNED"

    def test_post_deliveries_no_body_returns_400(self, client):
        resp = client.post("/deliveries", json={})
        assert resp.status_code == 400
        assert "order_id required" in resp.get_json()["error"]["message"]

    def test_post_deliveries_no_json_returns_400(self, client):
        resp = client.post("/deliveries", data="not json", content_type="application/json")
        assert resp.status_code == 400


class TestGetRoute:
    def test_get_delivery_by_id(self, client, existing_delivery):
        delivery_id = existing_delivery["id"]
        resp = client.get(f"/deliveries/{delivery_id}")
        assert resp.status_code == 200
        assert resp.get_json()["id"] == delivery_id

    def test_get_unknown_returns_404(self, client):
        resp = client.get("/deliveries/unknown")
        assert resp.status_code == 404

    def test_get_by_order(self, client):
        client.post("/deliveries", json={"order_id": "order-42"})
        resp = client.get("/orders/order-42/delivery")
        assert resp.status_code == 200
        assert resp.get_json()["order_id"] == "order-42"

    def test_get_by_unknown_order_returns_404(self, client):
        resp = client.get("/orders/unknown/delivery")
        assert resp.status_code == 404


class TestLocationRoute:
    def test_patch_location(self, client, existing_delivery):
        delivery_id = existing_delivery["id"]
        resp = client.patch(f"/deliveries/{delivery_id}/location", json={"location": {"lat": 48.8566, "lng": 2.3522}})
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "IN_TRANSIT"

    def test_patch_location_no_body_returns_400(self, client, existing_delivery):
        resp = client.patch(f"/deliveries/{existing_delivery['id']}/location", json={})
        assert resp.status_code == 400

    def test_patch_location_on_delivered_returns_422(self, client, existing_delivery):
        delivery_id = existing_delivery["id"]
        client.patch(f"/deliveries/{delivery_id}/location", json={"location": {"lat": 1, "lng": 2}})
        client.post(f"/deliveries/{delivery_id}/confirm")
        resp = client.patch(f"/deliveries/{delivery_id}/location", json={"location": {"lat": 3, "lng": 4}})
        assert resp.status_code == 422


class TestConfirmRoute:
    def test_confirm_returns_200(self, client, existing_delivery):
        resp = client.post(f"/deliveries/{existing_delivery['id']}/confirm")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "DELIVERED"

    def test_confirm_already_delivered_returns_422(self, client, existing_delivery):
        delivery_id = existing_delivery["id"]
        client.post(f"/deliveries/{delivery_id}/confirm")
        resp = client.post(f"/deliveries/{delivery_id}/confirm")
        assert resp.status_code == 422


class TestFailRoute:
    def test_fail_returns_200(self, client, existing_delivery):
        resp = client.post(f"/deliveries/{existing_delivery['id']}/fail", json={"reason": "Accident"})
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "FAILED"
