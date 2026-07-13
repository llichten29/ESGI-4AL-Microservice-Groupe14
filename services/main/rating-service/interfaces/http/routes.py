from flask import Blueprint, request, jsonify, current_app

from domain.models import RatingException

routes = Blueprint('rating', __name__, url_prefix='')


def _serialize_rating(r):
    return {
        "id": r.id,
        "order_id": r.order_id,
        "rater_id": r.rater_id,
        "rater_type": r.rater_type,
        "target_id": r.target_id,
        "target_type": r.target_type,
        "score": r.score,
        "comment": r.comment,
        "created_at": r.created_at
    }


def _serialize_summary(s):
    return {
        "target_id": s.target_id,
        "target_type": s.target_type,
        "average_score": s.average_score,
        "review_count": s.review_count
    }


def _service():
    return current_app.rating_service


def _error(e):
    return jsonify({"error": {"code": e.code, "message": e.message}}), e.status_code


@routes.route('/ratings', methods=['POST'])
def create_rating():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"code": "INVALID_INPUT", "message": "Request body required"}}), 400
        rating = _service().create_rating(data)
        return jsonify(_serialize_rating(rating)), 201
    except RatingException as e:
        return _error(e)


@routes.route('/ratings/<rating_id>', methods=['GET'])
def get_rating(rating_id):
    try:
        rating = _service().get_rating(rating_id)
        return jsonify(_serialize_rating(rating))
    except RatingException as e:
        return _error(e)


@routes.route('/ratings/target/<target_type>/<target_id>', methods=['GET'])
def get_target_ratings(target_type, target_id):
    ratings = _service().get_ratings_for_target(target_id, target_type.upper())
    return jsonify({"ratings": [_serialize_rating(r) for r in ratings]})


@routes.route('/ratings/target/<target_type>/<target_id>/summary', methods=['GET'])
def get_target_summary(target_type, target_id):
    summary = _service().get_summary(target_id, target_type.upper())
    return jsonify(_serialize_summary(summary))
