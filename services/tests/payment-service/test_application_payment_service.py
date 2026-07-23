import pytest


def _order_payment(card_token="card_ok", amount=42.0, order_id="order-1"):
    return {
        "order_id": order_id,
        "customer_id": "cust-1",
        "amount": amount,
        "card_token": card_token
    }


class TestProcessPayment:
    def test_successful_payment_is_completed(self, payment_service):
        payment = payment_service.process_payment(_order_payment())
        assert payment.status == "COMPLETED"
        assert payment.transaction_id.startswith("txn_")
        assert payment.completed_at

    def test_successful_payment_publishes_payment_processed(self, payment_service, mock_broker):
        payment = payment_service.process_payment(_order_payment())
        mock_broker.publish_event.assert_called_once()
        kwargs = mock_broker.publish_event.call_args.kwargs
        assert kwargs["exchange"] == "payment.events"
        assert kwargs["routing_key"] == "payment.processed"
        assert kwargs["event_data"]["order_id"] == "order-1"
        assert kwargs["event_data"]["payment_id"] == payment.id

    def test_declined_card_fails_without_retry(self, payment_service, mock_broker, fake_sleep, models):
        data = _order_payment(card_token="card_declined")
        with pytest.raises(models.PaymentDeclined):
            payment_service.process_payment(data)
        fake_sleep.assert_not_called()
        kwargs = mock_broker.publish_event.call_args.kwargs
        assert kwargs["routing_key"] == "payment.failed"

    def test_amount_over_limit_is_declined(self, payment_service, models):
        data = _order_payment(amount=750.0)
        with pytest.raises(models.PaymentDeclined):
            payment_service.process_payment(data)

    def test_flaky_gateway_succeeds_after_exponential_retries(self, payment_service, fake_sleep, mock_broker):
        payment = payment_service.process_payment(_order_payment(card_token="card_flaky"))
        assert payment.status == "COMPLETED"
        assert [call.args[0] for call in fake_sleep.call_args_list] == [1.0, 2.0]
        kwargs = mock_broker.publish_event.call_args.kwargs
        assert kwargs["routing_key"] == "payment.processed"

    def test_is_idempotent_per_order(self, payment_service, mock_broker):
        first = payment_service.process_payment(_order_payment())
        second = payment_service.process_payment(_order_payment())
        assert first.id == second.id
        assert mock_broker.publish_event.call_count == 1

    def test_rejects_missing_order_id(self, payment_service, models):
        with pytest.raises(models.PaymentException) as exc:
            payment_service.process_payment({"amount": 10.0})
        assert exc.value.status_code == 422

    def test_rejects_non_positive_amount(self, payment_service, models):
        data = _order_payment(amount=0)
        with pytest.raises(models.PaymentException) as exc:
            payment_service.process_payment(data)
        assert exc.value.status_code == 422


class TestRefund:
    def test_full_refund_marks_payment_refunded(self, payment_service, mock_broker):
        payment = payment_service.process_payment(_order_payment(amount=30.0))
        refunded = payment_service.refund(payment.id, reason="Order rejected")
        assert refunded.status == "REFUNDED"
        assert refunded.refunded_amount == 30.0
        kwargs = mock_broker.publish_event.call_args.kwargs
        assert kwargs["routing_key"] == "payment.refunded"
        assert kwargs["event_data"]["amount"] == 30.0

    def test_partial_refund_keeps_status_completed(self, payment_service):
        payment = payment_service.process_payment(_order_payment(amount=30.0))
        refunded = payment_service.refund(payment.id, amount=10.0, reason="Missing item")
        assert refunded.status == "COMPLETED"
        assert refunded.refunded_amount == 10.0

    def test_cannot_refund_more_than_paid(self, payment_service, models):
        payment = payment_service.process_payment(_order_payment(amount=30.0))
        with pytest.raises(models.InvalidRefund):
            payment_service.refund(payment.id, amount=50.0)

    def test_cannot_refund_failed_payment(self, payment_service, models):
        data = _order_payment(card_token="card_declined")
        with pytest.raises(models.PaymentDeclined):
            payment_service.process_payment(data)
        payment = payment_service.repository.find_by_order_id("order-1")
        with pytest.raises(models.InvalidRefund):
            payment_service.refund(payment.id)

    def test_refund_unknown_payment_raises_404(self, payment_service, models):
        with pytest.raises(models.PaymentNotFound) as exc:
            payment_service.refund("nope")
        assert exc.value.status_code == 404
