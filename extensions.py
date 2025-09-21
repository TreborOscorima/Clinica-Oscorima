from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from marshmallow import ValidationError

db = SQLAlchemy()
jwt = JWTManager()

def init_extensions(app):
    CORS(app, supports_credentials=True)
    db.init_app(app)
    jwt.init_app(app)

    @app.errorhandler(ValidationError)
    def handle_marshmallow_error(err):
        return {"message": "Datos inválidos", "errors": err.messages}, 400
