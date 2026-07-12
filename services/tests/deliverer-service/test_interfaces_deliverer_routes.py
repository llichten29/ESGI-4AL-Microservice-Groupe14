class TestDelivererRoutes:
    def test_post_deliverers_returns_201(self, deliverer_client):
        resp = deliverer_client.post('/deliverers', json={"name": "Marco", "vehicle": "SCOOTER"})
        assert resp.status_code == 201
        assert resp.get_json()["status"] == "AVAILABLE"

    def test_post_deliverers_no_body_returns_400(self, deliverer_client):
        resp = deliverer_client.post('/deliverers', json={})
        assert resp.status_code == 400

    def test_list_deliverers(self, deliverer_client):
        deliverer_client.post('/deliverers', json={"name": "Marco"})
        resp = deliverer_client.get('/deliverers')
        assert resp.status_code == 200
        assert len(resp.get_json()["deliverers"]) == 1

    def test_get_deliverer_by_id(self, deliverer_client):
        created = deliverer_client.post('/deliverers', json={"name": "Marco"}).get_json()
        resp = deliverer_client.get(f"/deliverers/{created['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Marco"

    def test_get_unknown_returns_404(self, deliverer_client):
        resp = deliverer_client.get('/deliverers/ghost')
        assert resp.status_code == 404

    def test_patch_availability(self, deliverer_client):
        deliverer = deliverer_client.post('/deliverers', json={"name": "Marco"}).get_json()
        resp = deliverer_client.patch(f"/deliverers/{deliverer['id']}/availability", json={"status": "OFFLINE"})
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "OFFLINE"

    def test_assign_available(self, deliverer_client):
        deliverer_client.post('/deliverers', json={"name": "Marco"})
        resp = deliverer_client.post('/deliverers/assign')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["deliverer"]["id"]
        assert data["deliverer"]["name"] == "Marco"

    def test_assign_when_none_available(self, deliverer_client):
        resp = deliverer_client.post('/deliverers/assign')
        assert resp.status_code == 200
        assert resp.get_json()["deliverer"] is None

    def test_release_deliverer(self, deliverer_client):
        created = deliverer_client.post('/deliverers', json={"name": "Marco"}).get_json()
        deliverer_client.post('/deliverers/assign')
        resp = deliverer_client.post(f"/deliverers/{created['id']}/release")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "AVAILABLE"
