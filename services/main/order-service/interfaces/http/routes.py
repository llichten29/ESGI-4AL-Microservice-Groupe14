from flask import Blueprint, request, jsonify, current_app

from domain.models import OrderException

routes = Blueprint('order', __name__, url_prefix='')


def _serialize_item(i):
    return {
        "dishId": i.dish_id,
        "name": i.name,
        "quantity": i.quantity,
        "unitPrice": i.unit_price,
        "subtotal": i.subtotal
    }


def _serialize_saga_step(s):
    return {"state": s.state, "detail": s.detail, "timestamp": s.timestamp}


def _serialize_order(o):
    return {
        "id": o.id,
        "customerId": o.customer_id,
        "restaurantId": o.restaurant_id,
        "restaurantName": o.restaurant_name,
        "items": [_serialize_item(i) for i in o.items],
        "deliveryFee": o.delivery_fee,
        "totalPrice": o.total_price,
        "deliveryAddress": o.delivery_address,
        "status": o.status,
        "sagaState": o.saga_state,
        "paymentId": o.payment_id,
        "deliveryId": o.delivery_id,
        "cancellationReason": o.cancellation_reason,
        "createdAt": o.created_at,
        "updatedAt": o.updated_at
    }


def _service():
    return current_app.order_service


def _error(e):
    return jsonify({"error": {"code": e.code, "message": e.message}}), e.status_code


@routes.route('/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": "Request body required"}}), 400
        order = _service().create_order(data)
        return jsonify(_serialize_order(order)), 201
    except OrderException as e:
        return _error(e)


@routes.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    try:
        order = _service().get_order(order_id)
        return jsonify(_serialize_order(order))
    except OrderException as e:
        return _error(e)


@routes.route('/orders/<order_id>', methods=['DELETE'])
def cancel_order(order_id):
    try:
        data = request.get_json(silent=True) or {}
        order = _service().cancel_order(order_id, data.get("reason", "Cancelled by customer"))
        return jsonify(_serialize_order(order))
    except OrderException as e:
        return _error(e)


@routes.route('/customers/<customer_id>/orders', methods=['GET'])
def get_customer_orders(customer_id):
    orders = _service().get_customer_orders(customer_id)
    return jsonify({"orders": [_serialize_order(o) for o in orders]})


@routes.route('/orders/<order_id>/saga', methods=['GET'])
def get_order_saga(order_id):
    try:
        order = _service().get_order(order_id)
        return jsonify({
            "orderId": order.id,
            "sagaState": order.saga_state,
            "history": [_serialize_saga_step(s) for s in order.saga_history]
        })
    except OrderException as e:
        return _error(e)


@routes.route('/orders/circuit-breakers', methods=['GET'])
def get_circuit_breakers():
    return jsonify({"circuitBreakers": _service().get_circuit_breakers()})
