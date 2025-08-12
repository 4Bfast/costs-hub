# run.py

from app import create_app

# Cria a instância da aplicação usando a nossa factory
app = create_app()

if __name__ == '__main__':
    # O host='0.0.0.0' permite que a aplicação seja acessível
    # de fora do container Docker (importante para o futuro)
    app.run(host='0.0.0.0', port=5000, debug=True)