from flask import Blueprint, request, jsonify, current_app

from domain.models import CatalogException

routes = Blueprint('catalog', __name__, url_prefix='')


def _serialize_dish(d):
    return {"id": d.id, "name": d.name, "price": d.price}


def _serialize_entry(e):
    return {
        "restaurantId": e.restaurant_id,
        "name": e.name,
        "cuisineType": e.cuisine_type,
        "address": e.address,
        "isOpen": e.is_open,
        "rating": e.rating,
        "reviewCount": e.review_count,
        "dishes": [_serialize_dish(d) for d in e.dishes],
        "indexedAt": e.indexed_at
    }


def _service():
    return current_app.catalog_service


@routes.route('/restaurants/search', methods=['GET'])
def search_restaurants():
    is_open = request.args.get('isOpen')
    result = _service().search_restaurants(
        query=request.args.get('query', ''),
        cuisine_type=request.args.get('cuisineType', ''),
        is_open=None if is_open is None else is_open.lower() == 'true',
        min_rating=float(request.args.get('minRating', 0) or 0),
        limit=int(request.args.get('limit', 20)),
        offset=int(request.args.get('offset', 0))
    )
    return jsonify({
        "total": result["total"],
        "restaurants": [_serialize_entry(e) for e in result["restaurants"]]
    })


@routes.route('/dishes/search', methods=['GET'])
def search_dishes():
    dishes = _service().search_dishes(
        query=request.args.get('query', ''),
        restaurant_id=request.args.get('restaurantId', ''),
        max_price=float(request.args.get('maxPrice', 0) or 0),
        limit=int(request.args.get('limit', 20))
    )
    return jsonify({"dishes": dishes})
