from flask import Blueprint, request, jsonify, current_app

from domain.models import RestaurantException

MSG_BODY_REQUIRED = "Request body required"

routes = Blueprint('restaurant', __name__, url_prefix='')


def _serialize_opening_hours(oh):
    return {"day": oh.day, "open_time": oh.open_time, "close_time": oh.close_time}


def _serialize_address(addr):
    if not addr:
        return None
    result = {"street": addr.street, "city": addr.city, "postal_code": addr.postal_code}
    if addr.coordinates:
        result["coordinates"] = {"latitude": addr.coordinates.latitude, "longitude": addr.coordinates.longitude}
    return result


def _serialize_menu_option(opt):
    return {"id": opt.id, "name": opt.name, "price": opt.price, "is_default": opt.is_default}


def _serialize_menu_item(item):
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "price": item.price,
        "is_available": item.is_available,
        "options": [_serialize_menu_option(o) for o in item.options]
    }


def _serialize_menu(menu):
    return {
        "id": menu.id,
        "name": menu.name,
        "is_active": menu.is_active,
        "items": [_serialize_menu_item(i) for i in menu.items]
    }


def _serialize_restaurant(r):
    return {
        "id": r.id,
        "name": r.name,
        "address": _serialize_address(r.address),
        "phone": r.phone,
        "cuisine_type": r.cuisine_type,
        "opening_hours": [_serialize_opening_hours(oh) for oh in r.opening_hours.values()],
        "is_open": r.is_open,
        "status": r.status,
        "rating": r.rating,
        "menus": [_serialize_menu(m) for m in r.menus],
        "created_at": r.created_at,
        "updated_at": r.updated_at
    }


def _service():
    return current_app.restaurant_service


def _error(e):
    return jsonify({"error": {"code": e.code, "message": e.message}}), e.status_code


# ---- Restaurant CRUD ----

@routes.route('/restaurants', methods=['POST'])
def create_restaurant():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": MSG_BODY_REQUIRED}}), 400
        restaurant = _service().create_restaurant(data)
        return jsonify(_serialize_restaurant(restaurant)), 201
    except RestaurantException as e:
        return _error(e)


@routes.route('/restaurants', methods=['GET'])
def list_restaurants():
    restaurants = _service().get_all_restaurants()
    return jsonify({"restaurants": [_serialize_restaurant(r) for r in restaurants]})


@routes.route('/restaurants/<restaurant_id>', methods=['GET'])
def get_restaurant(restaurant_id):
    try:
        restaurant = _service().get_restaurant(restaurant_id)
        return jsonify(_serialize_restaurant(restaurant))
    except RestaurantException as e:
        return _error(e)


@routes.route('/restaurants/<restaurant_id>', methods=['PUT'])
def update_restaurant(restaurant_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": MSG_BODY_REQUIRED}}), 400
        restaurant = _service().update_restaurant(restaurant_id, data)
        return jsonify(_serialize_restaurant(restaurant))
    except RestaurantException as e:
        return _error(e)


# ---- Menu CRUD ----

@routes.route('/restaurants/<restaurant_id>/menus', methods=['GET'])
def list_menus(restaurant_id):
    try:
        menus = _service().get_menus(restaurant_id)
        return jsonify({"menus": [_serialize_menu(m) for m in menus]})
    except RestaurantException as e:
        return _error(e)


@routes.route('/restaurants/<restaurant_id>/menus', methods=['POST'])
def create_menu(restaurant_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": MSG_BODY_REQUIRED}}), 400
        menu = _service().add_menu(restaurant_id, data)
        return jsonify(_serialize_menu(menu)), 201
    except RestaurantException as e:
        return _error(e)


@routes.route('/restaurants/<restaurant_id>/menus/<menu_id>', methods=['GET'])
def get_menu(restaurant_id, menu_id):
    try:
        menu = _service().get_menu(restaurant_id, menu_id)
        return jsonify(_serialize_menu(menu))
    except RestaurantException as e:
        return _error(e)


@routes.route('/restaurants/<restaurant_id>/menus/<menu_id>', methods=['PUT'])
def update_menu(restaurant_id, menu_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": MSG_BODY_REQUIRED}}), 400
        menu = _service().update_menu(restaurant_id, menu_id, data)
        return jsonify(_serialize_menu(menu))
    except RestaurantException as e:
        return _error(e)


@routes.route('/restaurants/<restaurant_id>/menus/<menu_id>', methods=['DELETE'])
def delete_menu(restaurant_id, menu_id):
    try:
        _service().delete_menu(restaurant_id, menu_id)
        return '', 204
    except RestaurantException as e:
        return _error(e)


# ---- Menu Items CRUD ----

@routes.route('/restaurants/<restaurant_id>/menus/<menu_id>/items', methods=['POST'])
def create_menu_item(restaurant_id, menu_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": MSG_BODY_REQUIRED}}), 400
        item = _service().add_menu_item(restaurant_id, menu_id, data)
        return jsonify(_serialize_menu_item(item)), 201
    except RestaurantException as e:
        return _error(e)


@routes.route('/restaurants/<restaurant_id>/menus/<menu_id>/items/<item_id>', methods=['GET'])
def get_menu_item(restaurant_id, menu_id, item_id):
    try:
        menu = _service().get_menu(restaurant_id, menu_id)
        for item in menu.items:
            if item.id == item_id:
                return jsonify(_serialize_menu_item(item))
        return jsonify({"error": {"code": "ITEM_NOT_FOUND", "message": f"Item {item_id} not found"}}), 404
    except RestaurantException as e:
        return _error(e)


@routes.route('/restaurants/<restaurant_id>/menus/<menu_id>/items/<item_id>', methods=['PUT'])
def update_menu_item(restaurant_id, menu_id, item_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": MSG_BODY_REQUIRED}}), 400
        item = _service().update_menu_item(restaurant_id, menu_id, item_id, data)
        return jsonify(_serialize_menu_item(item))
    except RestaurantException as e:
        return _error(e)


@routes.route('/restaurants/<restaurant_id>/menus/<menu_id>/items/<item_id>', methods=['DELETE'])
def delete_menu_item(restaurant_id, menu_id, item_id):
    try:
        _service().delete_menu_item(restaurant_id, menu_id, item_id)
        return '', 204
    except RestaurantException as e:
        return _error(e)


# ---- Order Management ----

@routes.route('/restaurants/<restaurant_id>/validate', methods=['POST'])
def validate_order(restaurant_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": MSG_BODY_REQUIRED}}), 400
        result = _service().validate_items(
            restaurant_id,
            data.get("items", []),
            data.get("requestedDeliveryTime")
        )
        return jsonify(result)
    except RestaurantException as e:
        return jsonify({"isValid": False, "reason": e.message, "code": e.code}), e.status_code


@routes.route('/restaurants/<restaurant_id>/orders/<order_id>/accept', methods=['POST'])
def accept_order(restaurant_id, order_id):
    try:
        data = request.get_json() or {}
        estimated_prep_time = data.get("estimatedPrepTime", 0)
        result = _service().accept_order(restaurant_id, order_id, estimated_prep_time)
        return jsonify(result)
    except RestaurantException as e:
        return _error(e)


@routes.route('/restaurants/<restaurant_id>/orders/<order_id>/reject', methods=['POST'])
def reject_order(restaurant_id, order_id):
    try:
        data = request.get_json() or {}
        reason = data.get("reason", "OTHER")
        result = _service().reject_order(restaurant_id, order_id, reason)
        return jsonify(result)
    except RestaurantException as e:
        return _error(e)


@routes.route('/restaurants/<restaurant_id>/orders/<order_id>/status', methods=['PATCH'])
def update_order_status(restaurant_id, order_id):
    try:
        data = request.get_json()
        if not data or "status" not in data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": "Status required"}}), 400
        result = _service().update_order_status(restaurant_id, order_id, data["status"])
        return jsonify(result)
    except RestaurantException as e:
        return _error(e)
