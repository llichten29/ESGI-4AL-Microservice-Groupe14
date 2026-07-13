class TestNotificationRules:
    def test_order_created_notifies_customer_and_restaurant(self, notification_service):
        notification_service.on_event("order.created", {
            "orderId": "order-1", "customerId": "cust-1", "restaurantId": "resto-1"
        })
        notifications = notification_service.get_notifications()
        assert len(notifications) == 2
        assert {n.recipient_type for n in notifications} == {"CUSTOMER", "RESTAURANT"}

    def test_payment_events_use_snake_case_payloads(self, notification_service):
        notification_service.on_event("payment.failed", {
            "order_id": "order-1", "customer_id": "cust-1", "reason": "Card declined"
        })
        notifications = notification_service.get_notifications(recipient_id="cust-1")
        assert len(notifications) == 1
        assert notifications[0].type == "PAYMENT_FAILED"
        assert "Card declined" in notifications[0].message

    def test_delivery_assigned_notifies_deliverer(self, notification_service):
        notification_service.on_event("delivery.assigned", {
            "order_id": "order-1", "deliverer_id": "del-1"
        })
        notifications = notification_service.get_notifications(recipient_id="del-1")
        assert len(notifications) == 1
        assert notifications[0].recipient_type == "DELIVERER"
        assert notifications[0].type == "DELIVERY_PROPOSAL"

    def test_order_cancelled_includes_reason(self, notification_service):
        notification_service.on_event("order.cancelled", {
            "orderId": "order-1", "customerId": "cust-1", "reason": "Payment failed"
        })
        notifications = notification_service.get_notifications(recipient_id="cust-1")
        assert "Payment failed" in notifications[0].message

    def test_unknown_routing_key_is_ignored(self, notification_service):
        notification_service.on_event("order.exotic", {"orderId": "order-1"})
        assert notification_service.get_notifications() == []

    def test_filter_by_type(self, notification_service):
        notification_service.on_event("order.created", {
            "orderId": "o1", "customerId": "cust-1", "restaurantId": "resto-1"
        })
        notification_service.on_event("order.delivered", {
            "orderId": "o1", "customerId": "cust-1"
        })
        delivered = notification_service.get_notifications(notification_type="ORDER_DELIVERED")
        assert len(delivered) == 1


class TestNotificationRoutes:
    def test_list_notifications_filtered_by_recipient(self, notification_service, notification_client):
        notification_service.on_event("order.confirmed", {"orderId": "o1", "customerId": "cust-1"})
        notification_service.on_event("order.confirmed", {"orderId": "o2", "customerId": "cust-2"})
        resp = notification_client.get('/notifications?recipient_id=cust-1')
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["notifications"]) == 1
        assert body["notifications"][0]["recipient_id"] == "cust-1"

    def test_get_notification_by_id(self, notification_service, notification_client):
        n = notification_service.notify("cust-1", "CUSTOMER", "TEST", "hello", {})
        resp = notification_client.get(f"/notifications/{n.id}")
        assert resp.status_code == 200
        assert resp.get_json()["message"] == "hello"

    def test_get_unknown_notification_returns_404(self, notification_client):
        resp = notification_client.get('/notifications/ghost')
        assert resp.status_code == 404
