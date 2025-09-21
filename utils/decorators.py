from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from flask import jsonify

def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role")
            if role not in roles:
                return jsonify({"message": "No autorizado"}), 403
            return fn(*args, **kwargs)
        return decorated
    return wrapper
