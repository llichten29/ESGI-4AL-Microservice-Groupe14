import logging

from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

routes = Blueprint('api_gateway', __name__)


@routes.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def proxy(path):
    gateway = current_app.gateway_service
    method = request.method
    full_path = f"/{path}"

    response_data, status_code = gateway.route_request(
        method=method,
        path=full_path,
        headers=dict(request.headers),
        body=request.get_json(silent=True)
    )

    return jsonify(response_data), status_code


@routes.route('/orders/<order_id>/details', methods=['GET'])
def order_details(order_id):
    gateway = current_app.gateway_service
    response_data, status_code = gateway.aggregate_order_details(
        order_id=order_id,
        headers=dict(request.headers)
    )
    return jsonify(response_data), status_code
