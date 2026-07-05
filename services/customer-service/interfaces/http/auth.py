import functools
import jwt
from flask import request, jsonify, g, current_app


def jwt_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"error": {"code": "MISSING_TOKEN", "message": "Authentication required"}}), 401

        try:
            secret = current_app.config.get("JWT_SECRET", "dev-secret")
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            g.current_user = payload.get("customer_id")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": {"code": "TOKEN_EXPIRED", "message": "Token has expired"}}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": {"code": "INVALID_TOKEN", "message": "Invalid token"}}), 401

        return f(*args, **kwargs)

    return decorated
