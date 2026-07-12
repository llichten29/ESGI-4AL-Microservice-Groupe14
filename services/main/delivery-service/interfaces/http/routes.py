from flask import Blueprint, request, jsonify, current_app

from domain.models import DeliveryException

routes = Blueprint('delivery', __name__, url_prefix='')


def _serialize_delivery(d):
    return {
        "id": d.id,
        "order_id": d.order_id,
        "deliverer_id": d.deliverer_id,
        "deliverer_name": d.deliverer_name,
        "customer_id": d.customer_id,
        "restaurant_id": d.restaurant_id,
        "status": d.status,
        "location": d.location,
        "assigned_at": d.assigned_at,
        "picked_up_at": d.picked_up_at,
        "delivered_at": d.delivered_at,
        "created_at": d.created_at,
        "updated_at": d.updated_at
    }


def _service():
    return current_app.delivery_service


def _error(e):
    return jsonify({"error": {"code": e.code, "message": e.message}}), e.status_code


@routes.route('/deliveries', methods=['POST'])
def assign_deliverer():
    try:
        data = request.get_json()
        if not data or "order_id" not in data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": "order_id required"}}), 400
        delivery = _service().assign_deliverer(
            order_id=data["order_id"],
            customer_id=data.get("customer_id", ""),
            restaurant_id=data.get("restaurant_id", "")
        )
        return jsonify(_serialize_delivery(delivery)), 201
    except DeliveryException as e:
        return _error(e)


@routes.route('/deliveries/<delivery_id>', methods=['GET'])
def get_delivery(delivery_id):
    try:
        delivery = _service().get_delivery(delivery_id)
        return jsonify(_serialize_delivery(delivery))
    except DeliveryException as e:
        return _error(e)


@routes.route('/orders/<order_id>/delivery', methods=['GET'])
def get_delivery_by_order(order_id):
    try:
        delivery = _service().get_delivery_by_order(order_id)
        return jsonify(_serialize_delivery(delivery))
    except DeliveryException as e:
        return _error(e)


@routes.route('/deliveries/<delivery_id>/location', methods=['PATCH'])
def update_location(delivery_id):
    try:
        data = request.get_json()
        if not data or "location" not in data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": "location required"}}), 400
        delivery = _service().update_location(delivery_id, data["location"])
        return jsonify(_serialize_delivery(delivery))
    except DeliveryException as e:
        return _error(e)


@routes.route('/deliveries/<delivery_id>/confirm', methods=['POST'])
def confirm_delivery(delivery_id):
    try:
        delivery = _service().confirm_delivery(delivery_id)
        return jsonify(_serialize_delivery(delivery))
    except DeliveryException as e:
        return _error(e)


@routes.route('/deliveries/<delivery_id>/fail', methods=['POST'])
def fail_delivery(delivery_id):
    try:
        data = request.get_json()
        reason = data.get("reason", "") if data else ""
        delivery = _service().fail_delivery(delivery_id, reason)
        return jsonify(_serialize_delivery(delivery))
    except DeliveryException as e:
        return _error(e)
