from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from .config import Config

# Inicializa as extensões do Flask, mas sem vincular a uma aplicação ainda
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    """
    Cria e configura uma instância da aplicação Flask.
    Este é o padrão Application Factory.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app, resources={r"/*": {"origins": "http://localhost:*"}}) #USAR ENV

    # Vincula as extensões à instância da aplicação
    db.init_app(app)
    migrate.init_app(app, db)

    # É crucial importar os modelos aqui para que o Flask-Migrate os reconheça
    from app import models
    from .routes import auth_bp, api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    from . import commands
    commands.init_app(app)

    return app