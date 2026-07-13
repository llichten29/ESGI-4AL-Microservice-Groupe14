from flask import Blueprint, request, jsonify, current_app

from domain.models import PaymentException

routes = Blueprint('payment', __name__, url_prefix='')


def _serialize_refund(r):
    return {
        "id": r.id,
        "amount": r.amount,
        "reason": r.reason,
        "created_at": r.created_at
    }


def _serialize_payment(p):
    return {
        "id": p.id,
        "order_id": p.order_id,
        "customer_id": p.customer_id,
        "amount": p.amount,
        "currency": p.currency,
        "payment_method": p.payment_method,
        "status": p.status,
        "transaction_id": p.transaction_id,
        "failure_reason": p.failure_reason,
        "refunds": [_serialize_refund(r) for r in p.refunds],
        "refunded_amount": p.refunded_amount,
        "created_at": p.created_at,
        "completed_at": p.completed_at
    }


def _service():
    return current_app.payment_service


def _error(e):
    return jsonify({"error": {"code": e.code, "message": e.message}}), e.status_code


@routes.route('/payments', methods=['POST'])
def process_payment():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": "Request body required"}}), 400
        payment = _service().process_payment(data)
        return jsonify(_serialize_payment(payment)), 201
    except PaymentException as e:
        return _error(e)


@routes.route('/payments/<payment_id>', methods=['GET'])
def get_payment(payment_id):
    try:
        payment = _service().get_payment(payment_id)
        return jsonify(_serialize_payment(payment))
    except PaymentException as e:
        return _error(e)


@routes.route('/orders/<order_id>/payment', methods=['GET'])
def get_payment_by_order(order_id):
    try:
        payment = _service().get_payment_by_order(order_id)
        return jsonify(_serialize_payment(payment))
    except PaymentException as e:
        return _error(e)


@routes.route('/payments/<payment_id>/refund', methods=['POST'])
def refund_payment(payment_id):
    try:
        data = request.get_json() or {}
        payment = _service().refund(
            payment_id,
            amount=data.get("amount", 0.0),
            reason=data.get("reason", "")
        )
        return jsonify(_serialize_payment(payment)), 201
    except PaymentException as e:
        return _error(e)
