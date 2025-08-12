# app/decorators.py

from functools import wraps
from flask import request, jsonify, current_app
import jwt
from .models import User

def token_required(f):
    """
    Decorator para garantir que um endpoint seja acessado apenas com um token JWT válido.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # O token é esperado no header 'Authorization' no formato 'Bearer <token>'
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Extrai o token, ignorando o "Bearer "
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Malformed token. Use "Bearer <token>" format.'}), 401

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            # Decodifica o token usando a mesma chave secreta e algoritmo
            # A biblioteca jwt já verifica a data de expiração (exp) e a assinatura
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            
            # Busca o usuário no banco de dados com base no 'sub' (ID do usuário) do token
            current_user = User.query.get(data['sub'])

            if not current_user:
                 return jsonify({'message': 'Token is invalid or user does not exist.'}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401

        # Passa o objeto do usuário logado para a rota real
        return f(current_user, *args, **kwargs)

    return decorated