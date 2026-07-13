class TestPaymentRoutes:
    def test_post_payments_returns_201(self, payment_client):
        resp = payment_client.post('/payments', json={
            "order_id": "order-1",
            "customer_id": "cust-1",
            "amount": 25.0,
            "card_token": "card_ok"
        })
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["status"] == "COMPLETED"
        assert body["order_id"] == "order-1"

    def test_post_payments_declined_returns_402(self, payment_client):
        resp = payment_client.post('/payments', json={
            "order_id": "order-1",
            "amount": 25.0,
            "card_token": "card_declined"
        })
        assert resp.status_code == 402
        assert resp.get_json()["error"]["code"] == "PAYMENT_DECLINED"

    def test_post_payments_invalid_input_returns_422(self, payment_client):
        resp = payment_client.post('/payments', json={"amount": 25.0})
        assert resp.status_code == 422

    def test_post_payments_without_body_returns_400(self, payment_client):
        resp = payment_client.post('/payments', content_type='application/json', data='null')
        assert resp.status_code == 400

    def test_get_payment_returns_payment(self, payment_client):
        created = payment_client.post('/payments', json={
            "order_id": "order-1", "amount": 25.0
        }).get_json()
        resp = payment_client.get(f"/payments/{created['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["id"] == created["id"]

    def test_get_unknown_payment_returns_404(self, payment_client):
        resp = payment_client.get('/payments/nope')
        assert resp.status_code == 404

    def test_get_payment_by_order(self, payment_client):
        payment_client.post('/payments', json={"order_id": "order-9", "amount": 12.0})
        resp = payment_client.get('/orders/order-9/payment')
        assert resp.status_code == 200
        assert resp.get_json()["order_id"] == "order-9"

    def test_refund_returns_201(self, payment_client):
        created = payment_client.post('/payments', json={
            "order_id": "order-1", "amount": 25.0
        }).get_json()
        resp = payment_client.post(f"/payments/{created['id']}/refund", json={"reason": "Rejected"})
        assert resp.status_code == 201
        assert resp.get_json()["status"] == "REFUNDED"

    def test_refund_too_large_returns_400(self, payment_client):
        created = payment_client.post('/payments', json={
            "order_id": "order-1", "amount": 25.0
        }).get_json()
        resp = payment_client.post(f"/payments/{created['id']}/refund", json={"amount": 99.0})
        assert resp.status_code == 400
