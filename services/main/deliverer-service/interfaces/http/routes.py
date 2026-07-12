from flask import Blueprint, request, jsonify, current_app

from domain.models import DeliveryException

routes = Blueprint('deliverer', __name__, url_prefix='')


def _serialize_deliverer(d):
    return {
        "id": d.id,
        "name": d.name,
        "phone": d.phone,
        "vehicle": d.vehicle,
        "status": d.status,
        "location": d.location,
        "created_at": d.created_at,
        "updated_at": d.updated_at
    }


def _service():
    return current_app.deliverer_service


def _error(e):
    return jsonify({"error": {"code": e.code, "message": e.message}}), e.status_code


@routes.route('/deliverers', methods=['POST'])
def register_deliverer():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": "Request body required"}}), 400
        deliverer = _service().register_deliverer(data)
        return jsonify(_serialize_deliverer(deliverer)), 201
    except DeliveryException as e:
        return _error(e)


@routes.route('/deliverers', methods=['GET'])
def list_deliverers():
    deliverers = _service().get_deliverers()
    return jsonify({"deliverers": [_serialize_deliverer(d) for d in deliverers]})


@routes.route('/deliverers/<deliverer_id>', methods=['GET'])
def get_deliverer(deliverer_id):
    try:
        deliverer = _service().get_deliverer(deliverer_id)
        return jsonify(_serialize_deliverer(deliverer))
    except DeliveryException as e:
        return _error(e)


@routes.route('/deliverers/<deliverer_id>/availability', methods=['PATCH'])
def set_availability(deliverer_id):
    try:
        data = request.get_json()
        if not data or "status" not in data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": "Status required"}}), 400
        deliverer = _service().set_availability(deliverer_id, data["status"])
        return jsonify(_serialize_deliverer(deliverer))
    except DeliveryException as e:
        return _error(e)


@routes.route('/deliverers/assign', methods=['POST'])
def assign_available():
    result = _service().assign_available()
    if not result:
        return jsonify({"deliverer": None}), 200
    return jsonify({"deliverer": result})


@routes.route('/deliverers/<deliverer_id>/release', methods=['POST'])
def release_deliverer(deliverer_id):
    try:
        deliverer = _service().release_deliverer(deliverer_id)
        return jsonify(_serialize_deliverer(deliverer))
    except DeliveryException as e:
        return _error(e)
