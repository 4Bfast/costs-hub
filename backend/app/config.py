# app/config.py

import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

class Config:
    """Configurações da aplicação."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'P0T2WIpbh6elqc0WHqT5YVtPrMG3bsPO'
    
    # Configuração do Banco de Dados com SQLAlchemy
    # A URL de conexão é lida da variável de ambiente DATABASE_URL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

