class TestRatingRoutes:
    def test_post_ratings_returns_201(self, rating_client):
        resp = rating_client.post('/ratings', json={
            "target_id": "rest-1", "target_type": "RESTAURANT",
            "score": 5, "comment": "Parfait!"
        })
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["score"] == 5
        assert body["target_id"] == "rest-1"

    def test_post_ratings_invalid_score_returns_422(self, rating_client):
        resp = rating_client.post('/ratings', json={
            "target_id": "rest-1", "score": 0
        })
        assert resp.status_code == 422

    def test_post_ratings_without_body_returns_400(self, rating_client):
        resp = rating_client.post('/ratings', content_type='application/json', data='null')
        assert resp.status_code == 400

    def test_get_rating_returns_rating(self, rating_client):
        created = rating_client.post('/ratings', json={
            "target_id": "rest-1", "score": 4
        }).get_json()
        resp = rating_client.get(f"/ratings/{created['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["id"] == created["id"]

    def test_get_unknown_rating_returns_404(self, rating_client):
        resp = rating_client.get('/ratings/ghost')
        assert resp.status_code == 404

    def test_get_target_ratings(self, rating_client):
        rating_client.post('/ratings', json={"target_id": "rest-1", "score": 5})
        rating_client.post('/ratings', json={"target_id": "rest-1", "score": 3})
        resp = rating_client.get('/ratings/target/RESTAURANT/rest-1')
        assert resp.status_code == 200
        assert len(resp.get_json()["ratings"]) == 2

    def test_get_target_summary(self, rating_client):
        rating_client.post('/ratings', json={"target_id": "rest-1", "score": 5})
        resp = rating_client.get('/ratings/target/RESTAURANT/rest-1/summary')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["average_score"] == 5.0
        assert body["review_count"] == 1
