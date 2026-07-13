from flask import Blueprint, request, jsonify, current_app

from domain.models import NotificationException

routes = Blueprint('notification', __name__, url_prefix='')


def _serialize_notification(n):
    return {
        "id": n.id,
        "recipient_id": n.recipient_id,
        "recipient_type": n.recipient_type,
        "type": n.type,
        "channel": n.channel,
        "message": n.message,
        "payload": n.payload,
        "created_at": n.created_at
    }


def _service():
    return current_app.notification_service


def _error(e):
    return jsonify({"error": {"code": e.code, "message": e.message}}), e.status_code


@routes.route('/notifications', methods=['GET'])
def list_notifications():
    notifications = _service().get_notifications(
        recipient_id=request.args.get('recipient_id', ''),
        notification_type=request.args.get('type', '')
    )
    return jsonify({"notifications": [_serialize_notification(n) for n in notifications]})


@routes.route('/notifications/<notification_id>', methods=['GET'])
def get_notification(notification_id):
    try:
        notification = _service().get_notification(notification_id)
        return jsonify(_serialize_notification(notification))
    except NotificationException as e:
        return _error(e)
