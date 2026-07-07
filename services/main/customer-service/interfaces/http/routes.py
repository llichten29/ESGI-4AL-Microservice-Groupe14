from flask import Blueprint, request, jsonify, g, current_app

from domain.models import CustomerException
from .auth import jwt_required

routes = Blueprint('customer', __name__, url_prefix='')


def _serialize_address(a):
    return {
        "id": a.id,
        "label": a.label,
        "street": a.street,
        "city": a.city,
        "postal_code": a.postal_code,
        "is_default": a.is_default
    }


def _serialize_customer(c):
    return {
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "addresses": [_serialize_address(a) for a in c.addresses],
        "created_at": c.created_at,
        "updated_at": c.updated_at
    }


def _serialize_order(o):
    return {
        "order_id": o.order_id,
        "status": o.status,
        "total": o.total,
        "date": o.date,
        "restaurant_name": o.restaurant_name
    }


def _service():
    return current_app.customer_service


def _error(e):
    return jsonify({"error": {"code": e.code, "message": e.message}}), e.status_code


@routes.route('/customers/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": "Request body required"}}), 400
        customer, token = _service().register(data)
        return jsonify({"customer": _serialize_customer(customer), "token": token}), 201
    except CustomerException as e:
        return _error(e)


@routes.route('/customers/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": "Request body required"}}), 400
        customer, token = _service().login(
            data.get("email", ""),
            data.get("password", "")
        )
        return jsonify({"customer": _serialize_customer(customer), "token": token})
    except CustomerException as e:
        return _error(e)


@routes.route('/customers/profile', methods=['GET'])
@jwt_required
def get_profile():
    try:
        customer = _service().get_profile(g.current_user)
        return jsonify(_serialize_customer(customer))
    except CustomerException as e:
        return _error(e)


@routes.route('/customers/profile', methods=['PUT'])
@jwt_required
def update_profile():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": "Request body required"}}), 400
        customer = _service().update_profile(g.current_user, data)
        return jsonify(_serialize_customer(customer))
    except CustomerException as e:
        return _error(e)


@routes.route('/customers/addresses', methods=['GET'])
@jwt_required
def get_addresses():
    try:
        addresses = _service().get_addresses(g.current_user)
        return jsonify({"addresses": [_serialize_address(a) for a in addresses]})
    except CustomerException as e:
        return _error(e)


@routes.route('/customers/addresses', methods=['POST'])
@jwt_required
def add_address():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": "Request body required"}}), 400
        address = _service().add_address(g.current_user, data)
        return jsonify(_serialize_address(address)), 201
    except CustomerException as e:
        return _error(e)


@routes.route('/customers/addresses/<address_id>', methods=['PUT'])
@jwt_required
def update_address(address_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": "Request body required"}}), 400
        address = _service().update_address(g.current_user, address_id, data)
        return jsonify(_serialize_address(address))
    except CustomerException as e:
        return _error(e)


@routes.route('/customers/addresses/<address_id>', methods=['DELETE'])
@jwt_required
def delete_address(address_id):
    try:
        _service().delete_address(g.current_user, address_id)
        return '', 204
    except CustomerException as e:
        return _error(e)


@routes.route('/customers/orders', methods=['GET'])
@jwt_required
def get_orders():
    try:
        orders = _service().get_orders(g.current_user)
        return jsonify({"orders": [_serialize_order(o) for o in orders]})
    except CustomerException as e:
        return _error(e)
