from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize extensions
app = Flask(__name__)
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app.config.from_object('project.app.config.secure')

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints (if any)
    # from .controller import oconvenerBP
    # app.register_blueprint(oconvenerBP)

    return app
