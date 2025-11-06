from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from .config import Config
import logging
import os
from logging.handlers import RotatingFileHandler

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

    # Configuração de CORS usando variáveis de ambiente
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:*').split(',')
    CORS(app, resources={r"/*": {"origins": cors_origins}})

    # Configuração de logging melhorada
    if not app.debug and not app.testing:
        # Configuração para produção
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/costshub.log', maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('CostsHub startup')
    else:
        # Configuração para desenvolvimento
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('backend.log'),
                logging.StreamHandler()
            ]
        )
        
        # Configurar logger específico para emails
        email_logger = logging.getLogger('email')
        email_logger.setLevel(logging.DEBUG)
        
        # Configurar logger específico para convites
        invite_logger = logging.getLogger('invite')
        invite_logger.setLevel(logging.DEBUG)

    # Vincula as extensões à instância da aplicação
    db.init_app(app)
    migrate.init_app(app, db)

    # É crucial importar os modelos aqui para que o Flask-Migrate os reconheça
    from app import models
    from .routes import auth_bp, api_bp, redirect_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(redirect_bp)  # Blueprint para redirecionamentos

    from . import commands
    commands.init_app(app)

    return app